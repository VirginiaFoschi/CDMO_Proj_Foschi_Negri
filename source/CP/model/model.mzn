include "globals.mzn";

% --- Parameters ---
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

% Symmetry breaking flag
bool: sym_break;

%--- Decision Variable ---
% for each weeke w and each game-slot k, matchPeriod[w,k] is the period to which that game is assigned
array[Weeks, 1..nPeriods] of var Periods: matchPeriod;

% --- Constraints ---

% For each week, the period assignments of all game-slots must be all different->  Every period in every week has exactly one game
constraint forall(w in Weeks)(
  alldifferent([matchPeriod[w,k] | k in 1..nPeriods])
);

% Counts how many times team t plays in period p across all weeks. This count must not exceed 2
constraint forall(t in Teams, p in Periods)(
    sum(w in Weeks, k in 1..nPeriods where team1[w,k] = t)( bool2int(matchPeriod[w,k] = p) )
  + sum(w in Weeks, k in 1..nPeriods where team2[w,k] = t)( bool2int(matchPeriod[w,k] = p) )
  <= 2
);


% --- Symmetry breaking ---

% Breaks Period symmetry
constraint sym_break -> forall(k in 1..nPeriods)(matchPeriod[1,k] = k);

solve satisfy;