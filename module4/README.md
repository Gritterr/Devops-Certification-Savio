# Module 4, Assignment 1: Continuous Integration with Jenkins

Jenkins jobs for the Sanders and Fresco web app (`../`), run on a local Jenkins LTS (2.580.1).

## Jobs and chain

Each job builds the repository folder directly (custom workspace, no SCM). Each job starts the next one on success.

| Job | Type | What it does | Triggers |
|---|---|---|---|
| DEVELOPER_COMPILE | Freestyle | `mvn clean compile` | DEVELOPER_CODE_REVIEW |
| DEVELOPER_CODE_REVIEW | Freestyle | `mvn checkstyle:check` (uses `../checkstyle.xml`) | QA_UNIT_TEST |
| QA_UNIT_TEST | Freestyle | `mvn test` with JaCoCo; publishes JUnit results | QA_METRICS_CHECK |
| QA_METRICS_CHECK | Freestyle | Converts JaCoCo to Cobertura XML; publishes coverage | QA_PACKAGE |
| QA_PACKAGE | Freestyle | `mvn package -DskipTests`; archives `target/*.war` | none |
| SAMPLE_COMPILE_VIEW | Build Pipeline View | Shows the chain, initial job DEVELOPER_COMPILE | n/a |

Exported job configs are in [jenkins-jobs/](jenkins-jobs/).

## Changes from the plan

- **Coverage tool.** The classic `cobertura-maven-plugin` fails on Java 26 (`ExceptionInInitializerError`). The Jenkins Cobertura plugin (1.17) is still installed, but it throws `NoClassDefFoundError: hudson/util/IOException2` on this Jenkins core, so it can't publish. Coverage is published with the Coverage plugin (`code-coverage-api`), which reads Cobertura XML.
- **Coverage conversion.** JaCoCo (`pom.xml`) writes `target/site/jacoco/jacoco.xml`. [tools/jacoco2cobertura.py](tools/jacoco2cobertura.py) converts it to `target/site/cobertura/coverage.xml`. Line hits are approximate: a line counts as hit if any instruction in it ran.
- **Coverage thresholds.** The Coverage plugin shows results without thresholds, so the build does not fail on low coverage. Current line coverage is about 25%, because `HelloServlet` has no tests yet.

## Results

Chain run #3: DEVELOPER_COMPILE, DEVELOPER_CODE_REVIEW, QA_UNIT_TEST, QA_METRICS_CHECK and QA_PACKAGE all finished SUCCESS. The Maven tests pass (3/3).

## Screenshots

- [screenshots/1-qa-unit-test-console.png](screenshots/1-qa-unit-test-console.png): QA_UNIT_TEST build #3 console output
- [screenshots/2-qa-metrics-dashboard.png](screenshots/2-qa-metrics-dashboard.png): QA_METRICS_CHECK build #3 with coverage (line 25%)
- [screenshots/3-qa-package-target-folder.png](screenshots/3-qa-package-target-folder.png): QA_PACKAGE workspace `target/` folder, including `sf-webapp.war`
- [screenshots/4-sample-compile-view-pipeline.png](screenshots/4-sample-compile-view-pipeline.png): SAMPLE_COMPILE_VIEW pipeline. Earlier QA_METRICS_CHECK runs (#1, #2) show red from the setup failures; run #3 is all green.

## Written answer: extending the pipeline with web and load tests

- **Web tests.** Add a downstream job after QA_PACKAGE. Deploy the WAR to a test Tomcat (the Module 3 deploy step, pointed at a test server), then run a Selenium or Playwright suite against it in headless mode. Publish results with the JUnit plugin so failures show on the pipeline view. Fail the build on test failures and keep the job chained, so the pipeline stops before any later stage.
- **Load tests.** Add another downstream job. Run Apache JMeter (or Gatling) in non-GUI mode against the deployed app, then publish results with the Performance plugin. Set thresholds for response time and error rate so the build fails when they are exceeded.
- **Ordering.** Compile, review, unit tests and packaging stay first. Web and load tests run only on a successful package, against a dedicated test environment rather than the developer machine.
