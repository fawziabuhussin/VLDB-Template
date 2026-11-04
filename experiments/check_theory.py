"""Exhaustive small-instance checks for the two new AVG propositions."""
from fractions import Fraction as F
from itertools import combinations_with_replacement, product
import json
from pathlib import Path

U=frozenset(range(3));sets=[frozenset(i for i in U if m>>i&1) for m in range(8)]

def good(B,S,tau):
 vals=[v for T,v in B if not T&S]
 return bool(vals) and sum(vals)<=tau*len(vals)

def optimum(B,tau):
 ss=[S for S in sets if good(B,S,tau)]
 return min(map(len,ss)) if ss else None

counts={'singleton_avg':0,'sign_separated_avg':0}
singletons=[S for S in sets if len(S)<=1]
for B in combinations_with_replacement(list(product(singletons,(-1,0,2))),3):
 for tau in (F(-1,2),F(0),F(1)):
  if sum(v for T,v in B)<=tau*len(B):continue
  F0=sum(v-tau for T,v in B)
  a={t:sum(v-tau for T,v in B if T=={t}) for t in U}
  out=[]
  for T0,v0 in B:
   if v0>tau:continue
   S=frozenset()
   for t in sorted(U-T0,key=lambda t:(-a[t],t)):
    if a[t]<=0:break
    S=S|{t}
    if sum(a[t] for t in S)>=F0:
     assert good(B,S,tau);out.append(S);break
  result=min(map(len,out)) if out else None
  assert result==optimum(B,tau),(B,tau,result,optimum(B,tau))
  counts['singleton_avg']+=1
for B in combinations_with_replacement(list(product(sets,(-1,0,2))),3):
 tau=F(0)
 if sum(v for T,v in B)<=0 or not any(v<0 for T,v in B):continue
 if any(any(t in T and v<0 for T,v in B) and any(t in T and v>0 for T,v in B) for t in U):continue
 allowed=U-frozenset().union(*(T for T,v in B if v<0))
 restricted=[S for S in sets if S<=allowed and good(B,S,tau)]
 result=min(map(len,restricted)) if restricted else None
 assert result==optimum(B,tau)
 for S in sets:
  if S<=allowed:
   G=sum(v for T,v in B if T&S)
   assert G>=0
   assert good(B,S,tau)==(G>=sum(v for T,v in B))
 counts['sign_separated_avg']+=1
print(json.dumps(counts))

# The overlap control used in the evaluation: greedy's tie order matters,
# and its three deletions exceed the independently enumerated optimum two.
B=[(frozenset(T),1) for T in [(0,3),(0,4),(1,3),(2,4)]]
S=frozenset()
while sum(v for T,v in B if T&S)<4:
 t=min(U.union({3,4})-S,key=lambda t:(-sum(v for T,v in B if t in T and not T&S),t))
 S=S|{t}
assert S=={0,1,2}
allsets=[frozenset(i for i in range(5) if mask>>i&1) for mask in range(32)]
assert min(len(S) for S in allsets if all(T&S for T,v in B))==2
print('Four-derivation control: greedy 3, exhaustive optimum 2.')
