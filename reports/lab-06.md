# Lab 6: workflow

Axel Alacache. This section is the workflow only. Tests, the image job, Cloud Run and the red-to-green repair are later pull requests.

## Run

Pull request #19, commit `cb273b95f7e5e342b9e64f58df571abf636a4959`.

- Workflow: `CI`
- Event: `pull_request`
- Run: https://github.com/BaptVic78/mlops-fri2-vant-bike-demand/actions/runs/42254284603
- Conclusion: `success`
- `lock` success, 2026-11-06T16:38:35Z to 2026-11-06T16:38:55Z
- `style` success, 2026-11-06T16:38:58Z to 2026-11-06T16:39:15Z
- `tests` success, 2026-11-06T16:39:17Z to 2026-11-06T16:39:42Z

The tests job printed:

```text
156 passed, 2 warnings in 14.14s
```

That line is from the runner log of job `128017586991`, step `uv run --locked pytest -q`. It is not a laptop run. The runner did not train a model and did not build an image.

The choices are in the README, section [CI](../README.md#ci).
