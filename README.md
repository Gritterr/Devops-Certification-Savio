# Sanders and Fresco Web App

Maven web application (WAR) built and deployed to Tomcat by a Jenkins pipeline.

## Project layout

| Path | Purpose |
|------|---------|
| `src/main/java` | Servlet (`/hello`) and greeting logic |
| `src/main/webapp` | Static pages |
| `src/test/java` | JUnit 5 unit tests |
| `checkstyle.xml` | Code review rules |
| `Jenkinsfile` | Pipeline: Compile, Code Review, Unit test, Package, Deploy |

## Pipeline stages

1. **Compile**: `mvn clean compile`
2. **Code Review**: `mvn checkstyle:check` (fails on violations)
3. **Unit test**: `mvn test` (results published to Jenkins)
4. **Package**: `mvn package` produces `target/sf-webapp.war` (archived)
5. **Deploy**: uploads the WAR to Tomcat's manager API at `/sf-webapp`

## Jenkins setup

1. Install plugins: Pipeline, Git, JUnit, Credentials Binding.
2. Under *Manage Jenkins > Tools*, add:
   - Maven named `Maven-3.9`
   - JDK named `JDK-17`
3. Under *Manage Jenkins > Credentials*, add a username/password credential with ID `tomcat-deployer`.
4. Create a *Pipeline* job pointing at this repository (Pipeline script from SCM, Jenkinsfile path `Jenkinsfile`).

## Tomcat setup (10.1 or later)

Add a deployer user to `conf/tomcat-users.xml`:

```xml
<role rolename="manager-script"/>
<user username="deployer" password="CHANGE_ME" roles="manager-script"/>
```

Then start Tomcat. The deploy stage calls `http://localhost:8080/manager/text/deploy`, so change `TOMCAT_URL` in the `Jenkinsfile` if Tomcat runs elsewhere.

## Run locally

```bash
mvn clean package         # compile, unit tests, package the WAR
mvn checkstyle:check      # code review (not bound to a lifecycle phase)
```

After deployment, open `http://localhost:8080/sf-webapp/` or `http://localhost:8080/sf-webapp/hello?name=DevOps`.
