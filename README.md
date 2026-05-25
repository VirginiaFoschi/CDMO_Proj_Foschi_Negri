# CDMO Project 2024/2025 - Sports Tournament Scheduling (STS)
This repository contains the implementation, experimental results, and report developed for the Combinatorial Decision Making and Optimization course project, academic year 2024/2025.

Authors: Foschi Virginia, Negri Marta

## Problem Description
Given a tournament of n teams (n even, n ≥ 4), schedule all games over n-1 weeks, each divided into n/2 periods of two slots (home and away), such that:
- Every team plays against every other team exactly once
- Every team plays exactly once per week
- Every team plays at most twice in the same period over the tournament

An optimization variant is also implemented, minimizing the imbalance between home and away games for each team.

## Project Structure
```
.
├── source/
│   ├── CP/        # Constraint Programming
│   ├── SAT/       # Propositional SAT
│   ├── SMT/       # Satisfiability Modulo Theories
│   └── MIP/       # Mixed Integer Programming
├── res/
│   ├── CP/        # Results: <n_teams>.json
│   ├── SAT/
│   ├── SMT/
│   └── MIP/
├── run_all.py
├── solution_checker.py
├── Dockerfile
└── requirements.txt
```
## Running Experiments
All experiments run inside Docker to guarantee full reproducibility.
### 1. Install Docker:
   
Download, install and start Docker Desktop from https://www.docker.com/get-started.

No other dependencies are required — all solvers and packages are installed inside the container.

### 2. Build the Image:
   
From the project root, build the image: 
```bash
docker build -t sts-img .
```
### 3. Run Experiments
The available values for `[OPTIONS]` are listed in the table below.

- **Option A — Run directly**

  ```bash
  docker run --rm -v ${PWD}/res:/app/res sts-img python run_all.py [OPTIONS]
  ```

- **Option B — Enter the container first and then run**

  ```bash
  # Open a shell inside the container
  docker run -it --rm -v ${PWD}/res:/app/res --entrypoint bash sts-img
  ```

  Then run:

  ```bash
  python run_all.py [OPTIONS]
  ```


Results are written to `res/<PARADIGM>/<n_teams>.json` on your local machine.

| Flag | Description |
|------|-------------|
| `-p`, `--paradigms` | Paradigms to run: `CP`, `SAT`, `SMT`, `MIP`, or `all` (default: `all`) |
| `-n`, `--nteams` | Team sizes (MUST BE EVEN!!!), e.g. 6 8 10. If omitted, each paradigm uses its own defaults |
| `-s`, `--solvers` | Solvers to use, or all for every valid solver per paradigm. Invalid solvers are skipped with a warning |
| `-m`, `--models` | Models to use: decision, optimized, or both. If omitted, uses paradigm defaults |
| `-t`, `--timeout` | Timeout per run in seconds. If omitted, uses paradigm defaults |
| `-sym`, `--sym_break` | Symmetry breaking: True, False, or both. If omitted, uses paradigm defaults |
| `-o`, `--output-dir` | Base output directory (default: res/) |

### Examples
- Run everything with each paradigm's own defaults:
  ```bash
  python run_all.py -p all
  ```
- Run only CP and MIP on small instances:
  ```bash
  python run_all.py -p CP MIP -n 6 8 10
  ```
- Run all paradigms with all their valid solvers, both with and without symmetry breaking:
  ```bash
  python run_all.py -p all -s all -sym True False
  ```
- Run only the optimization model with a custom timeout:
  ```bash
  python run_all.py -m optimized -t 120
  ```

### 4. Run a Single Paradigm
Each paradigm can also be run individually:
```bash
python source/CP/run.py -n 6 8 -t 120
```

## Check results
To verify that the generated results are valid, run the provided
`solution_checker.py` script by passing the folder containing the JSON
result files to be checked.

```bash
python solution_checker.py <results_folder>
```

(where <results_folder> can be either `res/CP`, `res/SAT`, `res/SMT`, `res/MIP`)