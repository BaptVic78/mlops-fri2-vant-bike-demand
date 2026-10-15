# Lab 1: Team workflow and check record

Record observed facts or blocked/not-run with reasons. This team worksheet is
not an individual's graded Week 1 report.

## Team and setup

- Team/repository: mlops-fri2-vant-bike-demand
- Week/date: 09/10/2026
- Members and temporary roles: Thomas Soubagne - evidence recorder, Axel Alacache - reviewer, Victor Rouleau - dev, Nils Giraud - dev
- Repository/authentication access checks: ________
- Mac version/architecture, Python and uv versions: ________
- Environment/preflight command and actual outcome: ________
- Working agreement and backlog links: ________
- Ignored outputs and secret-protection checks: ________

## Reviewed change and checks

- **Branch, pull request and checked commit:** Lab 1 feature branch, submitted through a pull request to the team repository and successfully merged. PR number, branch name and commit SHA to be added.

- **Substantive change and responsible contributor:** Improved the team name validation logic to reject empty or whitespace-only names. The implementation was corrected after identifying a failing test in `tests/lab1/test_team.py`.

- **Additional test and why it is useful:** Added or verified `test_rejects_blank_names`, which checks that invalid team names raise a `ValueError`. This prevents invalid inputs from being accepted and improves code reliability.

- **Reviewer observation, response and merge status:** The pull request was reviewed and eventually merged. The validation issue was corrected and the tests passed locally. Specific reviewer comments and responses should be confirmed from the PR history.

- **Local lint/format/test commands and actual results:** Executed `pytest` to validate the implementation. Initially, `test_rejects_blank_names` failed because the expected `ValueError` was not raised. After correcting the validation logic, all tests passed. Lint and formatting command results should be added if executed.

- **Intentional exercise failure versus infrastructure failures:** The initial failure was caused by an application validation issue, not an infrastructure problem. It was resolved by modifying the implementation. No infrastructure failure was identified during local testing.

- **CI check names, actual statuses and checked revision:** GitHub Actions checks were associated with the pull request. Exact check names, statuses and commit SHA should be copied from the PR's Checks tab.

- **Starter/reference/collaborator/other assistance:** Used the course starter repository and Lab 1 instructions. Collaborated with team members through GitHub and used ChatGPT for debugging assistance, Git commands and documentation guidance. The implementation and test results were verified locally.

## Lab 2 handover

- Next driver/reviewer: Thomas Soubagne
- Readiness and remaining blockers: ________
- One bounded next action and owner: ________
- Own-contribution links retained for each student's Week 1 report: ________

## Screenshots

Save images in `reports/images/` and embed them below, for example
`![PR checks on a1b2c3d](images/lab-01-pr-checks.png)`. Add one line saying what each
image shows and which commit or pull request it belongs to. Include at least the
failing and the passing `lab1` run, and the pull request checks. Crop to the
relevant part and hide tokens, passwords and personal data.

- Image and caption: ________
