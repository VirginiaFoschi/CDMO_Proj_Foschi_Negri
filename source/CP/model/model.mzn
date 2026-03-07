include "globals.mzn";

int: nTeams;
constraint nTeams mod 2 = 0;

int: nWeeks   = nTeams - 1;
int: nPeriods = nTeams div 2;

set of int: Teams   = 0..nTeams-1;
set of int: Weeks   = 1..nWeeks;
set of int: Periods = 1..nPeriods;

% Precomputed pairings using circle method: the game in week w, slot k is team1[w,k] vs team2[w,k]
array[Weeks, 1..nPeriods] of int: team1; %team1[w,k] = first team in game slot k of week w
array[Weeks, 1..nPeriods] of int: team2; %team2[w,k] = second team in game slot k of week w

bool: sym_break;

% teamMatch[t,w] = the match index k in which team t participates during week w-> tells in week w, which match involves team t (for example it team 3 plays in the 2nd match of week 5, then teamMatch[3,5]2=2)
array[Teams, Weeks] of 1..nPeriods: teamMatch =
    array2d(Teams, Weeks, [
        sum(k in 1..nPeriods)(
            k * bool2int(team1[w,k] = t \/ team2[w,k] = t)
        ) | t in Teams, w in Weeks
    ]);

% --- Decision Variables ---
% for each week w and each game-slot k, matchPeriod[w,k] is the period to which that game is assigned
array[Weeks, 1..nPeriods] of var Periods: matchPeriod;

% --- Constraints ---

% For each week, the period assignments of all game-slots must be all different->  Every period in every week has exactly one game
constraint forall(w in Weeks)(
    alldifferent([matchPeriod[w,k] | k in 1..nPeriods])
);

% every team plays at most twice in the same period over the tournament
constraint forall(t in Teams)(
    global_cardinality_low_up(
        [matchPeriod[w, teamMatch[t,w]] | w in Weeks],
        [p | p in Periods],
        [1 | _ in Periods],
        [2 | _ in Periods]
    )
);

% --- Symmetry breaking ---

% Breaks Period symmetry
constraint sym_break ->
    forall(k in 1..nPeriods)(matchPeriod[1,k] = k);

solve satisfy;