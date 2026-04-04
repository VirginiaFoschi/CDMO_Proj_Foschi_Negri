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


% --- PRECOMPUTATION ---

% teamMatch[t,w] = match index k involving team t in week w
array[Teams, Weeks] of 1..nPeriods: teamMatch =
    array2d(Teams, Weeks, [
        sum(k in 1..nPeriods)(
            k * bool2int(team1[w,k] = t \/ team2[w,k] = t)
        ) | t in Teams, w in Weeks
    ]);


% --- DECISION VARIABLES ---

array[Weeks, 1..nPeriods] of var Periods: matchPeriod;
% swap[w,k] = 0 -> team1 is home, team2 is away
% swap[w,k] = 1 -> team2 is home, team1 is away
% removes the overhead of the solver generating hidden "view variables" to translate booleans into integers
array[Weeks, 1..nPeriods] of var 0..1: swap;


% --- PERIOD ASSIGNMENT CONSTRAINTS ---

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


% --- SYMMETRY BREAKING ---

% Period-label symmetry
constraint sym_break ->
    forall(k in 1..nPeriods)( matchPeriod[1,k] = k );

% Global swap flip symmetry (Force the first match of the first week to not swap)
constraint sym_break -> swap[1,1] = 0;


% --- OBJECTIVE WITH BOUNDS ---

array[Teams] of var 0..nWeeks: homeCount;

constraint forall(t in Teams)(
    homeCount[t] = sum(w in Weeks)(
        let { int: m = teamMatch[t,w] } in
        if team1[w,m] == t then 1 - swap[w,m]
        else                    swap[w,m]
        endif
    )
);

% Implied: total home games = total matches
constraint sum(t in Teams)(homeCount[t]) = nWeeks * nPeriods;

int: L = 1;
int: U = nWeeks;

% homeGames + awayGames = nWeeks-> AwayGames = nWeeks - homeGames
% |homeGames - awayGames|
% = |homeGames - (nWeeks - homeGames)|
% = |homeGames - nWeeks + homeGames|
% = |2 * homeGames - nWeeks|

% The heavy absolute max function (kept as required)
var L..U: maxImbalance = max(t in Teams)(abs(2*homeCount[t] - nWeeks));

constraint maxImbalance mod 2 = 1;

% --- SOLVE ---

solve minimize maxImbalance;