include "globals.mzn";

% --- Parameters ---
int: nTeams = 14;
constraint nTeams mod 2 = 0;

int: nWeeks   = nTeams - 1;
int: nPeriods = nTeams div 2;

set of int: Teams   = 0..nTeams-1;
set of int: Weeks   = 1..nWeeks;
set of int: Periods = 1..nPeriods;

% ============================================================
% Circle Method (fixed pairings)
% We fix team 0, rotate teams 1..(nTeams-1)
% Week w:
%   match k=1 is (0 vs w)
%   matches k=2..nPeriods are symmetric around w on 1..nWeeks (mod nWeeks)
% ============================================================

function int: wrap1toM(int: z, int: m) =
  ((((z - 1) mod m) + m) mod m) + 1;   % always in 1..m

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

% ============================================================
% Decision Variables
% ============================================================

% Which period is each match assigned to in each week
array[Weeks, 1..nPeriods] of var Periods: matchPeriod;


% ============================================================
% Constraints
% ============================================================

% Constraint 1: Each period in each week has exactly one match
constraint forall(w in Weeks)(
  alldifferent([matchPeriod[w,k] | k in 1..nPeriods])
);

% Constraint 2: Each team plays at most twice in the same period over the tournament
% Count how many times each team plays in each period 
constraint forall(t in Teams, p in Periods)(
    sum(w in Weeks, k in 1..nPeriods where baseA[w,k] = t)( bool2int(matchPeriod[w,k] = p) )
  + sum(w in Weeks, k in 1..nPeriods where baseB[w,k] = t)( bool2int(matchPeriod[w,k] = p) )
  <= 2
);


% ============================================================
% Symmetry breaking
% ============================================================
constraint matchPeriod[1,1] = 1;
% SB1) Fix period assignment in week 1 (kills global renaming of periods)
constraint forall(w in 2..nWeeks)(
  lex_lesseq(
    [matchPeriod[1,k] | k in 1..nPeriods],
    [matchPeriod[w,k] | k in 1..nPeriods]
  ));

% SB2) Fix home/away orientation in week 1 (kills global flip of all homeAssignment)
% You can choose either:
%constraint forall(k in 1..nPeriods)(
%  homeAssignment[1,k] = true
%);

% ============================================================
% Solve
% ============================================================

solve satisfy;

% ============================================================
% Output
% ============================================================
output [
  "Matches:\n" ++
  concat([
    "Week " ++ show(w) ++ ": " ++
    concat([
      "("
      ++ show(baseA[w,k])
      ++ " vs "
      ++ show(baseB[w,k])
      ++ ") "
      | p in Periods, k in 1..nPeriods
        where fix(matchPeriod[w,k]) = p
    ])
    ++ "\n"
    | w in Weeks
  ])
];