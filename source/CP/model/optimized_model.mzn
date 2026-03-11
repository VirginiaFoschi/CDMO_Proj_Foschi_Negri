include "globals.mzn";

% --- Parameters ---

int: nTeams;
constraint nTeams mod 2 = 0;

int: nWeeks   = nTeams - 1;
int: nPeriods = nTeams div 2;

set of int: Teams   = 0..nTeams-1;
set of int: Weeks   = 1..nWeeks;
set of int: Periods = 1..nPeriods;

array[Weeks, 1..nPeriods] of int: team1;
array[Weeks, 1..nPeriods] of int: team2;

% Symmetry breaking flag
bool: sym_break;

% ================================================================
% PRECOMPUTATION  (evaluated at compile time — zero runtime cost)
% ================================================================

% teamMatch[t,w] = match index k involving team t in week w
array[Teams, Weeks] of 1..nPeriods: teamMatch =
    array2d(Teams, Weeks, [
        sum(k in 1..nPeriods)(
            k * bool2int(team1[w,k] = t \/ team2[w,k] = t)
        ) | t in Teams, w in Weeks
    ]);

% isTeam1[t,w] = true iff team t is in the team1 slot
array[Teams, Weeks] of bool: isTeam1 =
    array2d(Teams, Weeks, [
        team1[w, teamMatch[t,w]] = t | t in Teams, w in Weeks
    ]);

% ================================================================
% DECISION VARIABLES
% ================================================================

array[Weeks, 1..nPeriods] of var Periods: matchPeriod;
array[Weeks, 1..nPeriods] of var bool:    home;

% ================================================================
% PERIOD ASSIGNMENT CONSTRAINTS
% ================================================================

% C1: each week is a permutation of periods
constraint forall(w in Weeks)(
    alldifferent([matchPeriod[w,k] | k in 1..nPeriods])
);

% C2: each team uses every period 1 or 2 times
constraint forall(t in Teams)(
    global_cardinality_low_up(
        [matchPeriod[w, teamMatch[t,w]] | w in Weeks],
        [p | p in Periods],
        [1 | _ in Periods],
        [2 | _ in Periods]
    )
);

% ================================================================
% HOME / AWAY BALANCE
% ================================================================

int: L = nWeeks div 2;
int: U = L + 1;

array[Teams] of var L..U: homeCount;

constraint forall(t in Teams)(
    homeCount[t] = sum(w in Weeks)(
        let { int: m = teamMatch[t,w] } in
        if isTeam1[t,w] then bool2int(home[w,m])
        else                  bool2int(not home[w,m])
        endif
    )
);

% Implied: total home games = total matches
constraint sum(t in Teams)(homeCount[t]) = nWeeks * nPeriods;

% ================================================================
% SYMMETRY BREAKING
% ================================================================
% Period-label symmetry
constraint sym_break ->
    forall(k in 1..nPeriods)( matchPeriod[1,k] = k );

% Global home/away flip symmetry
constraint sym_break -> home[1,1] = true;

% ================================================================
% SOLVE
% ================================================================

% homeGames + awayGames = nWeeks-> AwayGames = nWeeks - homeGames
% |homeGames - awayGames|
% = |homeGames - (nWeeks - homeGames)|
% = |homeGames - nWeeks + homeGames|
% = |2 * homeGames - nWeeks|

var int: maxImbalance = max(t in Teams)(abs(2*homeCount[t] - nWeeks));

solve minimize maxImbalance;