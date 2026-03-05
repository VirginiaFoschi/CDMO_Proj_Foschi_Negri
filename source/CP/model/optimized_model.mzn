include "globals.mzn";

% ============================================================
% Parameters
% ============================================================
int: nTeams = 16;
constraint nTeams mod 2 = 0;

int: nWeeks   = nTeams - 1;
int: nPeriods = nTeams div 2;

set of int: Teams   = 0..nTeams-1;
set of int: Weeks   = 1..nWeeks;
set of int: Periods = 1..nPeriods;

function int: wrap1toM(int: z, int: m) =
  ((((z - 1) mod m) + m) mod m) + 1;

array[Weeks, 1..nPeriods] of int: baseA =
  array2d(Weeks, 1..nPeriods,
    [ if k = 1 then 0 else wrap1toM(w - (k-1), nWeeks) endif
      | w in Weeks, k in 1..nPeriods ]
  );

array[Weeks, 1..nPeriods] of int: baseB =
  array2d(Weeks, 1..nPeriods,
    [ if k = 1 then w else wrap1toM(w + (k-1), nWeeks) endif
      | w in Weeks, k in 1..nPeriods ]
  );

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

% Objective: minimize worst imbalance (0 is best; with bounds it should reach 0)
var 0..nWeeks: maxImbalance;
constraint maxImbalance = max([ abs(2*homeCount[t] - nWeeks) | t in Teams ]);

% ============================================================
% Symmetry breaking
% ============================================================
constraint matchPeriod[1,1] = 1;

constraint forall(w in 2..nWeeks)(
  lex_lesseq(
    [matchPeriod[1,k] | k in 1..nPeriods],
    [matchPeriod[w,k] | k in 1..nPeriods]
  )
);

% Remove global flip symmetry on home/away
constraint home[1,1] = true;
% ============================================================
% Solve
% ============================================================
solve minimize maxImbalance;

% ============================================================
% Output
% ============================================================
function string: match_str(int: w, int: k) =
  if fix(home[w,k]) then
    show(baseA[w,k]) ++ " vs " ++ show(baseB[w,k])
  else
    show(baseB[w,k]) ++ " vs " ++ show(baseA[w,k])
  endif;

output [
  "Home bounds: L=" ++ show(L) ++ ", U=" ++ show(U) ++ "\n\n" ++
  "Home count per team:\n" ++
  concat([ "Team " ++ show(t) ++ ": " ++ show(homeCount[t]) ++ "\n" | t in Teams ]) ++
  "\nSchedule:\n" ++
  concat([
    "Week " ++ show(w) ++ ": " ++
    concat([
      "(" ++ match_str(w,k) ++ ") "
      | p in Periods, k in 1..nPeriods
        where fix(matchPeriod[w,k]) = p
    ]) ++ "\n"
    | w in Weeks
  ])
];