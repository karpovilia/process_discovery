// Finite-resource execution of block-structured workflow nets.
// No threads, no GPU, no external randomness. Counter streams pair actions.
#include <algorithm>
#include <array>
#include <cmath>
#include <cstdint>
#include <cstring>
#include <queue>
#include <stdexcept>
#include <vector>

extern "C" {
struct Input {
 int ncases,ntrans,npools,nlabels,ngroups,nfeatures,mode,world;
 int action_kind,action_pool,max_operations,keep_records,verify;
 double horizon,dt,event_duration,event_threshold,trigger_threshold,action_cost,action_effect;
 uint64_t seed,initial_mark,final_mark,action_sources;
 const double *schedule; // arrival time, complexity, process id
 const uint64_t *inputs,*outputs,*first_labels;
 const int *labels,*pools,*groups,*choice_kind,*choice_option,*group_attribute;
 const int *capacity,*route_pool,*group_source,*group_pool,*group_driver;
 const double *duration_base,*duration_amplitude,*group_base,*group_complexity,*group_amplitude;
 const double *duration_coef,*duration_sigma,*route_coef;
 double load_scale,truth_onset,truth_saturation,noise_sigma,complexity_multiplier;
};
struct Output {int status,operations,completions,nsamples;double trigger,max_wip;};
static char last_error[512]; const char* simulation_error(){return last_error;}
size_t input_size(){return sizeof(Input);} size_t output_size(){return sizeof(Output);}
}

static uint64_t mix(uint64_t x){x+=0x9e3779b97f4a7c15ULL;x=(x^(x>>30))*0xbf58476d1ce4e5b9ULL;x=(x^(x>>27))*0x94d049bb133111ebULL;return x^(x>>31);}
static double uniform(uint64_t seed,int cid,int label,int visit,int kind,int channel){
 uint64_t h=mix(seed);h=mix(h^uint64_t(cid));h=mix(h^uint64_t(label+1));h=mix(h^uint64_t(visit));h=mix(h^uint64_t(kind));h=mix(h^uint64_t(channel));
 return (double(h>>11)+0.5)/9007199254740992.0;
}
struct Event {double time;uint64_t serial;int kind,cid,transition,node,pool,worker;};
struct Later {bool operator()(const Event&a,const Event&b)const{return a.time>b.time||(a.time==b.time&&a.serial>b.serial);}};
struct Job {int cid,transition;double ready,start,end,q,w,wp;int worker;};

extern "C" int simulate(const Input *in,Output *out,double *samples,double *records,double *completed){
 try{
 last_error[0]=0;const auto&I=*in;*out={0,0,0,0,-1.,0.};
 if(I.nfeatures!=6||I.nlabels>30||I.ntrans>120||I.npools>32||I.ncases<0||I.dt<=0)return out->status=90;
 std::priority_queue<Event,std::vector<Event>,Later> events;uint64_t serial=0;
 auto push=[&](double t,int k,int c=-1,int tr=-1,int node=-1,int pool=-1,int worker=-1){events.push({t,serial++,k,c,tr,node,pool,worker});};
 std::vector<std::queue<int>> queues(I.npools);std::vector<int> busy(I.npools,0),caps(I.capacity,I.capacity+I.npools);
 std::vector<std::vector<int>> occupied(I.npools);for(int p=0;p<I.npools;++p)occupied[p].resize(caps[p]+1,0);
 std::vector<uint64_t> marks(I.ncases,0);std::vector<int> pending(I.ncases,0),active(I.ncases,0),last(I.ncases,I.nlabels),seen_arrival(I.ncases,0);
 std::vector<int> visits(I.ncases*I.nlabels,0),decisions(I.ncases*(I.nlabels+1),0);
 std::vector<Job> jobs;jobs.reserve(std::min(I.max_operations,I.ncases*8));
 int arrived=0,done=0,pending_total=0,proc_w[2]={0,0},streak=0;
 bool triggered=false;double now=0.;
 auto context=[&](int cid,int source,bool start,int pool,double *x){
  int cl=int(I.schedule[cid*3+1]),pr=int(I.schedule[cid*3+2]);
  int qp=start?pool:I.route_pool[std::min(source,I.nlabels)*2+cl];
  if(qp<0||qp>=I.npools)qp=0;
  x[0]=1.;x[1]=cl;x[2]=pr;x[3]=std::log1p(double(queues[qp].size())/I.capacity[qp]);
  x[4]=std::log1p(double(arrived-done)/I.load_scale);x[5]=std::log1p(double(proc_w[pr])/I.load_scale);
 };
 auto choose=[&](int cid,const std::vector<int>&options){
  int tr=options[0],g=I.groups[tr],source=last[cid],cl=int(I.schedule[cid*3+1]),pr=int(I.schedule[cid*3+2]);
  if(g<0)throw std::runtime_error("unannotated conflict");
  for(int other:options)if(I.groups[other]!=g)throw std::runtime_error("non-local conflict");
  int visit=++decisions[cid*(I.nlabels+1)+source];
  double u=uniform(I.seed,cid,source,visit,1,0);
  // Explicit operational or training-derived guards are hard routing constraints.
  if(I.choice_kind[tr]==1 && I.group_attribute[g]>=0){
   int value=I.group_attribute[g]==0?cl:pr;
   for(int z:options)if(I.choice_option[z]==value)return z;
   throw std::runtime_error("class branch absent");
  }
  if(I.mode==0){
   if(I.choice_kind[tr]==1)throw std::runtime_error("truth XOR requires a guard");
   int qs=I.group_pool[g];double p=I.group_base[g]+I.group_complexity[g]*cl;
   if(I.world==2||I.world==3){double level=arrived-done;
    if(I.group_driver[g]==1)level=double(queues[qs].size());
    if(I.group_driver[g]==2)level=proc_w[pr];
    double onset=I.group_driver[g]==1?0.:I.truth_onset;
    double scale=I.group_driver[g]==1?2.*I.capacity[qs]:I.truth_saturation;
    double z=std::max(0.,level-onset)/scale;p+=I.group_amplitude[g]*z*z/(1.+z*z);
   }
   int actual_source=I.group_source[g];
   if(triggered&&I.action_kind==2&&(I.action_sources&(uint64_t(1)<<actual_source)))p*=I.action_effect;
   if(p<0.||p>=1.)throw std::runtime_error("invalid true route probability");
   int value=u<p?1:0;for(int z:options)if(I.choice_option[z]==value)return z;throw std::runtime_error("loop option absent");
  }
  double x[6];context(cid,source,false,0,x);std::vector<double> prob(I.nlabels+1);double maximum=-1e300;
  for(int a=0;a<=I.nlabels;++a){double v=0.;for(int f=0;f<6;++f)v+=x[f]*I.route_coef[(source*(I.nlabels+1)+a)*6+f];prob[a]=v;maximum=std::max(maximum,v);}
  double normalizer=0.;for(double &v:prob){v=std::exp(std::max(-40.,v-maximum));normalizer+=v;}for(double &v:prob)v/=normalizer;
  std::vector<double> weights;double sum=0.;int repeat=-1,exit=-1;
  for(int i=0;i<int(options.size());++i){int z=options[i];double v=0.;for(int a=0;a<=I.nlabels;++a)if(I.first_labels[z]&(uint64_t(1)<<a))v+=prob[a];v=std::max(1e-9,v);weights.push_back(v);sum+=v;
   if(I.choice_kind[z]==2){if(I.choice_option[z]==1)repeat=i;else exit=i;}
  }
  if(repeat>=0&&exit>=0&&options.size()==2){double p=std::clamp(weights[repeat]/sum,.001,.95);
   if(triggered&&I.action_kind==2&&(I.action_sources&(uint64_t(1)<<source)))p*=I.action_effect;
   return options[u<p?repeat:exit];
  }
  double target=u*sum;for(int i=0;i<int(options.size());++i){target-=weights[i];if(target<=0)return options[i];}return options.back();
 };
 auto advance=[&](int cid){
  for(int step=0;step<1000;++step){
   if(marks[cid]==I.final_mark&&pending[cid]==0){
    if(!active[cid])throw std::runtime_error("double completion");active[cid]=0;--proc_w[int(I.schedule[cid*3+2])];++done;
    completed[out->completions*4]=cid;completed[out->completions*4+1]=now;completed[out->completions*4+2]=now-I.schedule[cid*3];completed[out->completions*4+3]=I.schedule[cid*3+2];++out->completions;return;
   }
   std::vector<int> enabled;for(int tr=0;tr<I.ntrans;++tr)if((marks[cid]&I.inputs[tr])==I.inputs[tr])enabled.push_back(tr);
   if(enabled.empty())return;
   int tr=enabled[0];std::vector<int> conflict;for(int z:enabled)if(I.inputs[z]&I.inputs[tr])conflict.push_back(z);
   if(conflict.size()>1)tr=choose(cid,conflict);
   marks[cid]^=I.inputs[tr];
   if(I.labels[tr]<0){if(marks[cid]&I.outputs[tr])throw std::runtime_error("unsafe silent output");marks[cid]|=I.outputs[tr];}
   else{
    if(int(jobs.size())>=I.max_operations)throw std::runtime_error("operation limit");
    int node=int(jobs.size());jobs.push_back({cid,tr,now,0.,0.,0.,0.,0.,-1});queues[I.pools[tr]].push(node);++pending[cid];++pending_total;
   }
  }
  throw std::runtime_error("silent divergence");
 };
 auto start=[&](){
  for(int pool=0;pool<I.npools;++pool){while(!queues[pool].empty()&&busy[pool]<caps[pool]){
   int node=queues[pool].front(),cid=jobs[node].cid,tr=jobs[node].transition,a=I.labels[tr];
   double x[6];context(cid,a,true,pool,x);double q=queues[pool].size();queues[pool].pop();int worker=0;while(occupied[pool][worker])++worker;occupied[pool][worker]=1;++busy[pool];
   int visit=++visits[cid*I.nlabels+a];double u1=uniform(I.seed,cid,a,visit,0,0),u2=uniform(I.seed,cid,a,visit,0,1);
   double normal=std::sqrt(-2.*std::log(u1))*std::cos(6.2831853071795864769*u2);double logd;
   if(I.mode==0){double factor=1.;if(I.world==1||I.world==3)factor+=I.duration_amplitude[a]*q/(q+2.*I.capacity[pool]);
    double mean=I.duration_base[a]*(1.+I.complexity_multiplier*I.schedule[cid*3+1])*factor;
    logd=std::log(mean)-.5*I.noise_sigma*I.noise_sigma+I.noise_sigma*normal;
   }else{logd=0.;for(int f=0;f<6;++f)logd+=x[f]*I.duration_coef[a*6+f];logd=std::clamp(logd+I.duration_sigma[a]*normal,-4.,5.);}
   double d=std::exp(logd);if(!std::isfinite(d)||d<=0)throw std::runtime_error("bad duration");
   Job &job=jobs[node];job.start=now;job.end=now+d;job.q=q;job.w=arrived-done;job.wp=proc_w[int(I.schedule[cid*3+2])];job.worker=pool*1000+worker;
   push(now+d,1,cid,tr,node,pool,worker);
  }}
 };
 for(int cid=0;cid<I.ncases;++cid)push(I.schedule[cid*3],0,cid);
 for(int k=0;k<=int(std::floor(I.horizon/I.dt+1e-8));++k)push(k*I.dt,2);
 while(!events.empty()){
  Event event=events.top();events.pop();now=event.time;if(now>I.horizon)break;
  if(event.kind==0){int cid=event.cid;if(seen_arrival[cid])throw std::runtime_error("duplicate arrival");seen_arrival[cid]=1;active[cid]=1;marks[cid]=I.initial_mark;++arrived;++proc_w[int(I.schedule[cid*3+2])];advance(cid);start();}
  else if(event.kind==1){
   int cid=event.cid,tr=event.transition,a=I.labels[tr];--busy[event.pool];occupied[event.pool][event.worker]=0;--pending[cid];--pending_total;
   if(marks[cid]&I.outputs[tr])throw std::runtime_error("unsafe completion output");marks[cid]|=I.outputs[tr];last[cid]=a;
   Job job=jobs[event.node];
   if(I.keep_records){double *row=records+out->operations*16;int cl=int(I.schedule[cid*3+1]);int rp=I.route_pool[a*2+cl];
    row[0]=cid;row[1]=a;row[2]=cl;row[3]=I.schedule[cid*3+2];row[4]=job.ready;row[5]=job.start;row[6]=now;row[7]=job.q;row[8]=job.w;row[9]=job.wp;row[10]=std::log(now-job.start);row[11]=job.worker;
    row[12]=queues[rp].size();row[13]=arrived-done;row[14]=proc_w[int(I.schedule[cid*3+2])];row[15]=visits[cid*I.nlabels+a];
   }
   ++out->operations;advance(cid);start();
  }else{
   int w=arrived-done;
   if(!triggered&&I.action_kind!=0&&I.trigger_threshold>=0){streak=w>=I.trigger_threshold?streak+1:0;if(streak>=2){triggered=true;out->trigger=now;if(I.action_kind==1)++caps[I.action_pool];start();}}
   double *row=samples+out->nsamples*(8+I.npools);row[0]=now;row[1]=w;row[2]=done;row[3]=triggered;row[4]=proc_w[0];row[5]=proc_w[1];row[6]=arrived;row[7]=pending_total;
   int jobs_pending=0;for(int p=0;p<I.npools;++p){row[8+p]=busy[p];jobs_pending+=busy[p]+queues[p].size();if(busy[p]>caps[p]||busy[p]<0)throw std::runtime_error("capacity violation");}
   if(jobs_pending!=pending_total||proc_w[0]+proc_w[1]!=w)throw std::runtime_error("WIP accounting");
   if(I.verify){int count=0;for(int v:active)count+=v;if(count!=w)throw std::runtime_error("unique case WIP");}
   ++out->nsamples;
  }
  out->max_wip=std::max(out->max_wip,double(arrived-done));
 }
 if(out->operations>=I.max_operations)throw std::runtime_error("record limit");
 return out->status=0;
 }catch(const std::exception &e){std::strncpy(last_error,e.what(),511);return out->status=1;}
}
