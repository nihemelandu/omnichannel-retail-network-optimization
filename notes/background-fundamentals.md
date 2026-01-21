The objective function of a two-stage stochastic MILP is difficult to minimize because it includes an expected optimal recourse cost. While the recourse problem for a fixed first-stage decision and a fixed realization of uncertainty is tractable, the difficulty arises from taking the expectation over the optimal recourse cost across all possible realizations of uncertainty.
# Two-Stage Stochastic MILP: Fundamental Concepts

## Mathematical Expression

The general form of a two-stage stochastic MILP is:

$$\min_{x \in X} \{ c^T x + \mathbb{E}_{\xi}[Q(x, \xi)] \}$$

### Components

- **$x$**: First-stage (here-and-now) decisions made before uncertainty is revealed
- **$\xi$**: Random vector representing uncertainty
- **$Q(x, \xi)$**: Second-stage recourse function (optimal value of the recourse problem for given $x$ and realization $\xi$)
- **$\mathbb{E}_{\xi}[Q(x, \xi)]$**: Expected recourse cost (expectation taken over all possible realizations of $\xi$)
- **$c^T x$**: First-stage cost (deterministic, linear in $x$)
- **$X$**: Feasible set for first-stage decisions

## The Recourse Function

The second-stage recourse function $Q(x, \xi)$ is defined as:

$$Q(x, \xi) = \min_{y} \{ q(\xi)^T y : W(\xi)y \geq h(\xi) - T(\xi)x, \, y \in Y \}$$

where:
- **$y$**: Second-stage (recourse) decisions made after observing $\xi$
- **$q(\xi)$**: Second-stage cost coefficients
- **$W(\xi)$**: Recourse matrix
- **$T(\xi)$**: Technology matrix linking first-stage and second-stage decisions
- **$h(\xi)$**: Right-hand side vector
- **$Y$**: Feasible set for second-stage decisions (may include integrality constraints)

## Problem Classification

The two-stage stochastic MILP is typically:

- **Nonlinear Programming**: Despite $c^T x$ being linear, $\mathbb{E}_{\xi}[Q(x, \xi)]$ is generally **nonlinear** in $x$
- **Convex**: The expected recourse function is convex (if minimization problem)
- **Nonsmooth**: The function typically has kinks and is non-differentiable at certain points

### Why $\mathbb{E}_{\xi}[Q(x, \xi)]$ is Nonlinear

- $Q(x, \xi)$ is the optimal value of a linear program for each $\xi$
- As a function of $x$, it is **piecewise linear** and **convex**
- The expectation averages these piecewise linear functions, resulting in a **nonlinear, nonsmooth, convex** function

## Sample Average Approximation (SAA)

Since computing $\mathbb{E}_{\xi}[Q(x, \xi)]$ is often intractable, SAA approximates it using a finite sample:

### SAA Problem

$$\min_{x \in X} \{ c^T x + \frac{1}{N} \sum_{i=1}^{N} Q(x, \xi^i) \}$$

where $\\{\xi^1, \xi^2, \ldots, \xi^N\\}$ are independent samples drawn from the distribution of $\xi$.

### SAA Properties

- **Unbiased estimator**: $\mathbb{E}[\frac{1}{N} \sum_{i=1}^{N} Q(x, \xi^i)] = \mathbb{E}_{\xi}[Q(x, \xi)]$
- **Convergence**: As $N \to \infty$, the SAA solution converges to the true stochastic solution (by Law of Large Numbers)
- **Computational advantage**: Transforms intractable expectation into a finite sum (deterministic equivalent)

## Special Case: Finite Discrete Distribution

If $\xi$ has a finite discrete distribution with scenarios $\\{\xi^1, \ldots, \xi^S\\}$ and probabilities $\\{p_1, \ldots, p_S\\}$:

$$\mathbb{E}_{\xi}[Q(x, \xi)] = \sum_{s=1}^{S} p_s Q(x, \xi^s)$$

This can be reformulated as a **large-scale deterministic MILP** (deterministic equivalent formulation) by introducing scenario-specific variables.
