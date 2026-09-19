using System.Text.Json;

// Separate Monte Carlo harness. Warm-started safeguarded Newton solves the
// multiplier equation independently of Python's fixed bisection. Checkpoints
// are exported and compared with the actual application likelihood function.
record Scenario(double Draw, double Rho, double Elo1, bool UnderH1, int Seed, bool Paired = true);
record Checkpoint(int[] Bins, double Elo0, double Elo1, double Llr);
record Result(Scenario Scenario, int Trials, int Errors, int Unresolved, double MeanSamples, int MaxSamples, List<Checkpoint> Checkpoints);

static class Program
{
    static double Score(double elo) => 1 / (1 + Math.Pow(10, -elo / 400));
    static double Root(int[] bins, double target, ref double previous)
    {
        double lower = -1 / (1 - target), upper = 1 / target;
        double theta = Math.Clamp(previous, lower + 1e-13, upper - 1e-13);
        double total = bins.Sum() + bins.Count(n => n == 0) * .001;
        for (int iteration = 0; iteration < 150; iteration++)
        {
            double f = 0, derivative = 0;
            for (int k = 0; k < bins.Length; k++)
            {
                double weight = bins[k] == 0 ? .001 : bins[k];
                double delta = (double)k / (bins.Length - 1) - target;
                double ratio = delta / (1 + theta * delta);
                f += weight * ratio; derivative -= weight * ratio * ratio;
            }
            if (Math.Abs(f) < 1e-13 * total || upper - lower < 1e-13) break;
            if (f > 0) lower = theta; else upper = theta;
            double candidate = theta - f / derivative;
            theta = candidate > lower && candidate < upper ? candidate : (lower + upper) / 2;
        }
        previous = theta; return theta;
    }
    static double Llr(int[] bins, double s0, double s1, ref double t0, ref double t1)
    {
        Root(bins, s0, ref t0); Root(bins, s1, ref t1);
        double result = 0;
        for (int k = 0; k < bins.Length; k++)
        {
            double weight = bins[k] == 0 ? .001 : bins[k];
            double x = (double)k / (bins.Length - 1);
            result += weight * Math.Log((1 + t0 * (x - s0)) / (1 + t1 * (x - s1)));
        }
        return result;
    }
    static Result Run(Scenario scenario, int trials)
    {
        double mean = Score(scenario.UnderH1 ? scenario.Elo1 : 0), draw = scenario.Draw;
        double loss = (1 - draw) / 2 - (mean - .5), win = (1 - draw) / 2 + (mean - .5);
        double[] probabilities = [loss * loss, 2 * loss * draw, draw * draw + 2 * loss * win, 2 * win * draw, win * win];
        double[] identical = [loss, 0, draw, 0, win];
        for (int k = 0; k < 5; k++) probabilities[k] = (1 - scenario.Rho) * probabilities[k] + scenario.Rho * identical[k];
        if (!scenario.Paired) probabilities = [loss, draw, win];
        if (probabilities.Any(x => x < 0)) throw new ArgumentException("Invalid sampling distribution");
        for (int k = 1; k < probabilities.Length; k++) probabilities[k] += probabilities[k - 1];
        double lower = Math.Log(.05 / .95), upper = -lower, s0 = .5, s1 = Score(scenario.Elo1);
        int errors = 0, unresolved = 0, longest = 0; long pairs = 0;
        var checkpoints = new List<Checkpoint>(); var rng = new Random(scenario.Seed);
        for (int trial = 0; trial < trials; trial++)
        {
            int[] bins = new int[probabilities.Length]; double t0 = 0, t1 = 0; bool stopped = false;
            for (int n = 1; n <= 200000; n++)
            {
                double u = rng.NextDouble(); int k = 0; while (k < probabilities.Length - 1 && u >= probabilities[k]) k++; bins[k]++;
                double llr = Llr(bins, s0, s1, ref t0, ref t1);
                if (!double.IsFinite(llr)) throw new InvalidOperationException("Non-finite simulated likelihood");
                bool boundary = llr <= lower || llr >= upper;
                if (trial < 3 && (n is 1 or 2 or 5 or 10 or 100 or 1000 || boundary)) checkpoints.Add(new Checkpoint((int[])bins.Clone(), 0, scenario.Elo1, llr));
                if (boundary)
                {
                    if ((llr >= upper) != scenario.UnderH1) errors++;
                    pairs += n; longest = Math.Max(longest, n); stopped = true; break;
                }
            }
            if (!stopped) { unresolved++; pairs += 200000; longest = 200000; }
        }
        return new Result(scenario, trials, errors, unresolved, (double)pairs / trials, longest, checkpoints);
    }
    static void Main(string[] args)
    {
        string output = args.Length > 0 ? args[0] : "test-output/statistics-sprt-simulation.json";
        int trials = args.Length > 1 ? int.Parse(args[1]) : 2000;
        var scenarios = new List<Scenario>();
        foreach (double draw in new[] { .5, .9, .99 })
            foreach (double rho in new[] { 0.0, .6 })
                foreach (bool h1 in new[] { false, true }) scenarios.Add(new Scenario(draw, rho, draw == .99 ? 1 : 5, h1, 7970 + scenarios.Count * 977));
        foreach (double draw in new[] { .5, .9, .99 })
            foreach (bool h1 in new[] { false, true }) scenarios.Add(new Scenario(draw, 0, draw == .99 ? 1 : 5, h1, 7970 + scenarios.Count * 977, false));
        var results = new Result[scenarios.Count];
        Parallel.For(0, scenarios.Count, new ParallelOptions { MaxDegreeOfParallelism = 2 }, i => {
            results[i] = Run(scenarios[i], trials);
            Console.WriteLine(JsonSerializer.Serialize(new { scenario = scenarios[i], errors = results[i].Errors, trials, unresolved = results[i].Unresolved, mean_samples = results[i].MeanSamples }));
        });
        Directory.CreateDirectory(Path.GetDirectoryName(Path.GetFullPath(output))!);
        File.WriteAllText(output, JsonSerializer.Serialize(results, new JsonSerializerOptions { WriteIndented = true }));
        Console.WriteLine("Saved " + Path.GetFullPath(output));
    }
}
