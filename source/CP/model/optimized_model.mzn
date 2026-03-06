include "globals.mzn";

% ============================================================
% Parameters
% ============================================================
int: nTeams;
constraint nTeams mod 2 = 0;

int: nWeeks   = nTeams - 1;
int: nPeriods = nTeams div 2;

set of int: Teams   = 0..nTeams-1;
set of int: Weeks   = 1..nWeeks;
set of int: Periods = 1..nPeriods;

array[Weeks, 1..nPeriods] of int: baseA;
array[Weeks, 1..nPeriods] of int: baseB;

% Symmetry breaking flag
bool: sym_break;

array[Weeks, 1..nPeriods] of var Periods: matchPeriod;

% home[w,k] = true  => baseA[w,k] home, baseB away
% home[w,k] = false => baseB[w,k] home, baseA away
array[Weeks, 1..nPeriods] of var bool: home;

% ============================================================
% Constraints
% ============================================================

% C1: Each period in each week has exactly one match
constraint forall(w in Weeks)(
  alldifferent([matchPeriod[w,k] | k in 1..nPeriods])
);

% C2: Each team plays at most twice in the same period over the tournament
constraint forall(t in Teams, p in Periods)(
    sum(w in Weeks, k in 1..nPeriods where baseA[w,k] = t)(
      bool2int(matchPeriod[w,k] = p)
    )
  + sum(w in Weeks, k in 1..nPeriods where baseB[w,k] = t)(
      bool2int(matchPeriod[w,k] = p)
    )
  <= 2
);

% ============================================================
% Home/Away balance with tight bounds
% ============================================================

% Each team plays nWeeks matches. Perfect balance is impossible when nWeeks is odd.
int: L = nWeeks div 2;            % floor((nWeeks)/2)
int: U = L + (nWeeks mod 2);      % ceil((nWeeks)/2)

% FIX: build arrays indexed by Teams using array1d(Teams, ...)
array[Teams] of var 0..nWeeks: homeCount =
  array1d(Teams, [
    sum(w in Weeks, k in 1..nPeriods)(
        bool2int( home[w,k] /\ (baseA[w,k] = t) )
      + bool2int( (not home[w,k]) /\ (baseB[w,k] = t) )
    )
    | t in Teams
  ]);

% Tight bounds: homeCount[t] in [L..U]
constraint forall(t in Teams)( L <= homeCount[t] /\ homeCount[t] <= U );

% Optional explicit awayCount (implied, but fine)
array[Teams] of var 0..nWeeks: awayCount =
  array1d(Teams, [ nWeeks - homeCount[t] | t in Teams ]);
constraint forall(t in Teams)( L <= awayCount[t] /\ awayCount[t] <= U );

array[Teams] of var 0..nWeeks: imbalance =
    array1d(Teams,
        [ abs(homeCount[t] - awayCount[t]) | t in Teams ]
    );

% Objective: minimize worst imbalance (0 is best; with bounds it should reach 0)
var 0..nWeeks: maxImbalance = max(imbalance);
%Since nTeams is even, we know: nWeeks = nTeams - 1 and so each team plays an odd number of matches. This means that perfect balance is impossible, ie the optimal difference between home and away games is always 1
constraint maxImbalance >= 1;

% ============================================================
% Symmetry breaking
% ============================================================
constraint sym_break ->
  forall(k in 1..nPeriods)(
      matchPeriod[1,k] = k
  );

constraint sym_break -> forall(w in 2..nWeeks)(
  lex_lesseq(
    [matchPeriod[1,k] | k in 1..nPeriods],
    [matchPeriod[w,k] | k in 1..nPeriods]
  )
);

% Remove global flip symmetry on home/away
constraint sym_break ->
forall(k in 1..nPeriods)(
    home[1,k] = true
);
% ============================================================
% Solve
% ============================================================
solve minimize maxImbalance;