# Project roadmap

This list describes proposed improvements, not promises or completed work. Priorities reflect maintainability and practical user value.

## Engineering
- [ ] Establish CI with Python syntax, manifest validation and both MCP regression suites.
- [ ] Verify test suites pass in GitHub Actions; fix or isolate flaky network tests based on evidence.
- [ ] Investigate whether Supervisor admin permissions and `SYS_ADMIN` can be reduced without impairing intended tools.
- [ ] Add authentication/authorization regression tests for protected MCP routes.
- [ ] Add release smoke tests against a disposable Home Assistant test environment.
- [ ] Publish independently tagged GitHub Releases for each add-on after validation.

## Documentation and onboarding
- [ ] Record a real Full MCP + Lifeboat recovery demonstration.
- [ ] Add redacted screenshots from a test installation.
- [ ] Add a compatibility matrix based on versions actually tested.
- [ ] Collect and document common installation errors and their solutions.
- [ ] Create a public GitHub profile README in a separate `minermartijn/minermartijn` repository.

## Community and feedback
- [ ] Introduce the project to Home Assistant users with a reproducible demo.
- [ ] Document genuine external installs and feedback, with permission where appropriate.
- [ ] Triage issues and publish changelogs for meaningful updates.
- [ ] Accept focused external contributions and maintain visible review history.

## Sponsorship evidence

Measure what actually occurs: external issues, reproducible bugs fixed, merged human contributions, documented deployments, and citations from third-party projects. Do **not** manufacture stars, forks, installs, downloads, reviews or contributions.

The source of truth for completed work is merged code, passing checks, published releases and verifiable user reports.
