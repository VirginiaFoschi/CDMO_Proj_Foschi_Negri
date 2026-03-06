include "globals.mzn";

% --- Parameters ---
int: nTeams;
constraint nTeams mod 2 = 0;

int: nWeeks   = nTeams - 1;
int: nPeriods = nTeams div 2;

set of int: Teams   = 0..nTeams-1;
set of int: Weeks   = 1..nWeeks;
set of int: Periods = 1..nPeriods;

% Precomputed pairings (can be passed from Python)
array[Weeks, 1..nPeriods] of int: baseA;
array[Weeks, 1..nPeriods] of int: baseB;

% Symmetry breaking flag
bool: sym_break;


% Decision Variables
array[Weeks, 1..nPeriods] of var Periods: matchPeriod;

% Constraints
constraint forall(w in Weeks)(
  alldifferent([matchPeriod[w,k] | k in 1..nPeriods])
);

constraint forall(t in Teams, p in Periods)(
    sum(w in Weeks, k in 1..nPeriods where baseA[w,k] = t)( bool2int(matchPeriod[w,k] = p) )
  + sum(w in Weeks, k in 1..nPeriods where baseB[w,k] = t)( bool2int(matchPeriod[w,k] = p) )
  <= 2
);

% Symmetry breaking
constraint sym_break -> matchPeriod[1,1] = 1;
constraint sym_break -> forall(w in 2..nWeeks)(
  lex_lesseq(
    [matchPeriod[1,k] | k in 1..nPeriods],
    [matchPeriod[w,k] | k in 1..nPeriods]
  ));

solve satisfy;