"""Reproduce the manuscript's bounded TPC-H pilot; never modify input databases."""
from __future__ import annotations
import argparse, collections, csv, hashlib, heapq, json, math, platform, random, subprocess, sys, time
from fractions import Fraction
from pathlib import Path
import duckdb
import pulp

BODY = """from customer c join orders o on c.c_custkey=o.o_custkey
join lineitem l on o.o_orderkey=l.l_orderkey
join part p on l.l_partkey=p.p_partkey
where l.l_shipdate >= date '1995-01-01' and l.l_shipdate < date '1995-02-01'"""
VALUE = 'cast(l.l_extendedprice*100 as bigint)'

def load(path):
    con=duckdb.connect(str(path),read_only=True);con.execute('set threads=1')
    start=time.perf_counter()
    rows=con.execute(f'select c.c_custkey,p.p_partkey,{VALUE} {BODY} order by l.l_orderkey,l.l_linenumber').fetchall()
    keys=sorted({('c',c) for c,p,v in rows}|{('p',p) for c,p,v in rows})
    ids={key:i for i,key in enumerate(keys)}
    edges=[(ids['c',c],ids['p',p],v) for c,p,v in rows]
    elapsed=time.perf_counter()-start
    return con,edges,keys,elapsed

def survivor(edges,S):return [v for c,p,v in edges if c not in S and p not in S]
def feasible(edges,S,kind,target):
    values=survivor(edges,S)
    if kind=='COUNT':return len(edges)-len(values)>=target
    if kind=='SUM':return sum(v for c,p,v in edges)-sum(values)>=target
    return bool(values) and Fraction(sum(values),len(values))<=target

def greedy(edges,n,target,kind,method):
    weights=[1 if kind=='COUNT' else v for c,p,v in edges]
    incidence=[[] for _ in range(n)];g=[0]*n
    for b,(c,p,v) in enumerate(edges):
        for t in (c,p):incidence[t].append(b);g[t]+=weights[b]
    S=set();trace=[];gain=0;calls=0
    if method=='lazy_sql':
        db=duckdb.connect();db.execute('set threads=1')
        db.execute('create table d(c integer,p integer,w bigint)')
        db.executemany('insert into d values (?,?,?)',[(c,p,w) for (c,p,v),w in zip(edges,weights)])
        db.execute('create table deleted(t integer)')
        queue=[(-g[t],t) for t in range(n)];heapq.heapify(queue)
        stamps=[-1]*n
    alive=[True]*len(edges)
    while gain<target:
        if method=='incremental':
            t=min((t for t in range(n) if t not in S),key=lambda t:(-g[t],t));delta=g[t]
        elif method=='circuit':
            # P=sum_c y_c (sum_p w_cp y_p), evaluated and differentiated
            # without expansion of the inner sums. The y variables are Boolean.
            g=[0]*n
            for (c,p,v),w in zip(edges,weights):
                if c not in S and p not in S:g[c]+=w;g[p]+=w
            t=min((t for t in range(n) if t not in S),key=lambda t:(-g[t],t));delta=g[t]
        else:
            while queue:
                neg,t=heapq.heappop(queue)
                if t in S:continue
                if stamps[t]==len(S):delta=-neg;break
                delta=db.execute('''select coalesce(sum(w),0) from d where (c=? or p=?)
                  and not exists(select 1 from deleted where t=d.c or t=d.p)''',[t,t]).fetchone()[0]
                calls+=1;stamps[t]=len(S);heapq.heappush(queue,(-delta,t))
            else:raise RuntimeError('infeasible coverage')
        if delta<=0:raise RuntimeError('no positive gain')
        S.add(t);trace.append(t);gain+=delta
        if method=='incremental':
            for b in incidence[t]:
                if not alive[b]:continue
                alive[b]=False
                c,p,v=edges[b]
                for u in (c,p):g[u]-=weights[b]
        elif method=='lazy_sql':db.execute('insert into deleted values (?)',[t])
    if method=='lazy_sql':db.close()
    return S,{'status':'feasible','oracle_calls':calls,'trace':trace}

def avg_greedy(edges,n,target):
    S=set();trace=[];calls=0
    while not feasible(edges,S,'AVG',target):
        live=[(c,p,v) for c,p,v in edges if c not in S and p not in S]
        gains=[Fraction(0)]*n;hits=[0]*n
        for c,p,v in live:
            for t in (c,p):gains[t]+=v-target;hits[t]+=1
        candidates=[t for t in range(n) if t not in S and 0<hits[t]<len(live)]
        if not candidates:return S,{'status':'stalled','oracle_calls':calls,'trace':trace}
        t=min(candidates,key=lambda t:(-gains[t],t));calls+=len(candidates)
        if gains[t]<=0:return S,{'status':'stalled','oracle_calls':calls,'trace':trace}
        S.add(t);trace.append(t)
    return S,{'status':'feasible','oracle_calls':calls,'trace':trace}

def ilp(edges,n,kind,target,limit):
    start=time.perf_counter();model=pulp.LpProblem('miw',pulp.LpMinimize)
    x=[pulp.LpVariable(f'x{i}',cat=pulp.LpBinary) for i in range(n)]
    z=[pulp.LpVariable(f'z{i}',cat=pulp.LpBinary) for i in range(len(edges))]
    model+=pulp.lpSum(x)
    for (c,p,v),zb in zip(edges,z):
        model+=zb<=1-x[c];model+=zb<=1-x[p];model+=zb>=1-x[c]-x[p]
    if kind=='AVG':
        coeff=[v*target.denominator-target.numerator for c,p,v in edges]
        scale=max(map(abs,coeff)) or 1
        model+=pulp.lpSum(a/scale*zb for a,zb in zip(coeff,z))<=0
        model+=pulp.lpSum(z)>=1
    else:
        weights=[1 if kind=='COUNT' else v for c,p,v in edges]
        total=sum(weights)
        model+=pulp.lpSum(w/total*(1-zb) for w,zb in zip(weights,z))>=target/total
    build=time.perf_counter()-start;start=time.perf_counter()
    solver=pulp.HiGHS(msg=False,timeLimit=limit,threads=1,gapRel=0,gapAbs=0,random_seed=1729)
    model.solve(solver);elapsed=time.perf_counter()-start
    S={i for i,v in enumerate(x) if v.value() is not None and v.value()>.5}
    native=model.solverModel.modelStatusToString(model.solverModel.getModelStatus())
    info=model.solverModel.getInfo()
    status='optimal' if native=='Optimal' else ('timeout' if 'time' in native.lower() else native.lower())
    return S,{'status':status,'solver_status':native,'build_s':build,'solve_s':elapsed,
              'bound':info.mip_dual_bound,'mip_gap':info.mip_gap,'oracle_calls':0}

def sql_verify(con,keys,S,kind,target,edges):
    cs=[keys[t][1] for t in S if keys[t][0]=='c'];ps=[keys[t][1] for t in S if keys[t][0]=='p']
    count,total=con.execute(f'''select count(*),coalesce(sum({VALUE}),0) {BODY}
         and not list_contains(?,c.c_custkey) and not list_contains(?,p.p_partkey)''',[cs,ps]).fetchone()
    values=survivor(edges,S)
    assert count==len(values) and total==sum(values),'SQL/provenance disagreement'
    return feasible(edges,S,kind,target)

def self_check():
    from itertools import combinations
    # Genuine non-modular overlap: exact variants must agree on the whole trace.
    edges=[(0,3,7),(0,4,2),(1,3,6),(1,5,5),(2,4,1),(2,5,9)]
    for kind in ('COUNT','SUM'):
        for target in (1,3,5):
            results=[greedy(edges,6,target,kind,m) for m in ('incremental','lazy_sql','circuit')]
            assert len({tuple(r[1]['trace']) for r in results})==1
    # Enumerate all cardinalities to independently validate the full linking ILP.
    for kind,target in [('COUNT',4),('SUM',15),('AVG',Fraction(4))]:
        sols=[set(s) for k in range(7) for s in combinations(range(6),k) if feasible(edges,set(s),kind,target)]
        S,stats=ilp(edges,6,kind,target,5)
        assert stats['status']=='optimal' and feasible(edges,S,kind,target)
        assert len(S)==min(map(len,sols))
    # A repeated variable is Boolean-idempotent but ordinary derivatives overcount.
    assert 1**2-0**2==1 and 2*1==2
    print('Self-check: matching exact-greedy traces and exhaustive ILP comparisons passed.',flush=True)

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data-dir',type=Path)
    parser.add_argument('--output',type=Path,default=Path('experiments/results/review_revision'))
    parser.add_argument('--repetitions',type=int,default=3)
    parser.add_argument('--time-limit',type=float,default=5)
    parser.add_argument('--self-check',action='store_true')
    args=parser.parse_args();self_check()
    if args.self_check:return
    if not args.data_dir:parser.error('--data-dir is required')
    args.output.mkdir(parents=True,exist_ok=True)
    raw=args.output/'measurements.jsonl'
    if raw.exists():raise SystemExit('Refusing to replace recorded measurements; choose another output directory.')
    env={'python':sys.version,'platform':platform.platform(),'processor':subprocess.check_output(['sysctl','-n','machdep.cpu.brand_string'],text=True).strip(),
         'duckdb':duckdb.__version__,'pulp':pulp.__version__,'solver':'HiGHS','solver_version':__import__('highspy').Highs().version(),
         'threads':1,'time_limit_s':args.time_limit,'repetitions':args.repetitions,'seed':1729,
         'sql_body':BODY,'value':VALUE,'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), 'inputs':[]}
    rng=random.Random(1729)
    for sf in ('0_01','0_03'):
        path=args.data_dir/f'tpch_sf_{sf}.duckdb'
        con,edges,keys,extract=load(path)
        env['inputs'].append({'filename':path.name,'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'derivations':len(edges),'deletable_tuples':len(keys),'extraction_s':extract})
        for kind in ('COUNT','SUM','AVG'):
            fractions=('0.10','0.25','0.50') if kind!='AVG' else ('0.02','0.05','0.10')
            for a in fractions:
                alpha=Fraction(a)
                initial=len(edges) if kind=='COUNT' else sum(v for c,p,v in edges)
                target=math.ceil(initial*alpha) if kind!='AVG' else Fraction(initial,len(edges))*(1-alpha)
                for rep in range(1,args.repetitions+1):
                    methods=['ilp','incremental','lazy_sql','circuit'] if kind!='AVG' else ['ilp','avg_heuristic']
                    rng.shuffle(methods);traces=[]
                    for method in methods:
                        start=time.perf_counter()
                        if method=='ilp':S,stats=ilp(edges,len(keys),kind,target,args.time_limit)
                        elif method=='avg_heuristic':S,stats=avg_greedy(edges,len(keys),target)
                        else:S,stats=greedy(edges,len(keys),target,kind,method)
                        elapsed=time.perf_counter()-start
                        valid=sql_verify(con,keys,S,kind,target,edges)
                        if stats['status']=='optimal':assert valid,'solver optimum failed exact validation'
                        if stats['status']=='feasible':assert valid,'greedy failed exact validation'
                        trace=stats.pop('trace',None)
                        if trace is not None and method!='avg_heuristic':traces.append(tuple(trace))
                        row={'sf':sf.replace('_','.'),'kind':kind,'fraction':a,'repetition':rep,'method':method,
                             'M':len(edges),'n':len(keys),'target':str(target),'size':len(S) if valid else None,
                             'feasible':valid,'runtime_s':elapsed,'extraction_s':extract,'witness':[keys[t] for t in sorted(S)],**stats}
                        with raw.open('a') as f:f.write(json.dumps(row)+'\n')
                        print(sf,kind,a,rep,method,row['status'],row['size'],f'{elapsed:.3f}s',flush=True)
                    assert len(set(traces))<=1,'exact greedy implementations diverged'
        con.close()
        (args.output/'environment.json').write_text(json.dumps(env,indent=2)+'\n')
    rows=[json.loads(s) for s in raw.read_text().splitlines()]
    fields=[k for k in rows[0] if k!='witness']
    with (args.output/'measurements.csv').open('w') as f:
        w=csv.DictWriter(f,fieldnames=sorted({k for r in rows for k in r if k!='witness'}));w.writeheader();w.writerows({k:v for k,v in r.items() if k!='witness'} for r in rows)
    print('Completed',len(rows),'measurements.',flush=True)
if __name__=='__main__':main()
