#!/usr/bin/env python3
"""Generate the Jenkins job and view configs (jobs/*.xml) from scripts/*.sh.

Run after editing a script:  python3 build-job-configs.py
Then load a job into Jenkins with:  POST <jenkins>/job/<name>/config.xml
"""
from pathlib import Path
from xml.sax.saxutils import escape

HERE = Path(__file__).parent
REPO_URL = "https://github.com/Gritterr/projCert.git"
BRANCH = "*/master"

JOB1 = "Job1-Puppet-Agent"
JOB2 = "Job2-Ansible-Docker"
JOB3 = "Job3-Build-Deploy-PHP"


def script(name):
    return escape((HERE / "scripts" / name).read_text())


def git_scm():
    return f"""<scm class="hudson.plugins.git.GitSCM" plugin="git">
    <configVersion>2</configVersion>
    <userRemoteConfigs><hudson.plugins.git.UserRemoteConfig><url>{REPO_URL}</url></hudson.plugins.git.UserRemoteConfig></userRemoteConfigs>
    <branches><hudson.plugins.git.BranchSpec><name>{BRANCH}</name></hudson.plugins.git.BranchSpec></branches>
    <doGenerateSubmoduleConfigurations>false</doGenerateSubmoduleConfigurations>
    <submoduleCfg class="empty-list"/>
    <extensions/>
  </scm>"""


def trigger_next(job):
    return f"""<hudson.tasks.BuildTrigger>
      <childProjects>{job}</childProjects>
      <threshold><name>SUCCESS</name><ordinal>0</ordinal><color>BLUE</color><completeBuild>true</completeBuild></threshold>
    </hudson.tasks.BuildTrigger>"""


def job(description, node, builders, scm="<scm class=\"hudson.scm.NullSCM\"/>",
        triggers="<triggers/>", publishers="", properties="<properties/>"):
    return f"""<?xml version="1.1" encoding="UTF-8"?>
<project>
  <description>{escape(description)}</description>
  <keepDependencies>false</keepDependencies>
  {properties}
  {scm}
  <assignedNode>{node}</assignedNode>
  <canRoam>false</canRoam>
  <disabled>false</disabled>
  <blockBuildWhenDownstreamBuilding>false</blockBuildWhenDownstreamBuilding>
  <blockBuildWhenUpstreamBuilding>false</blockBuildWhenUpstreamBuilding>
  {triggers}
  <concurrentBuild>false</concurrentBuild>
  <builders>
    <hudson.tasks.Shell><command>{builders}</command></hudson.tasks.Shell>
  </builders>
  <publishers>
    {publishers}
  </publishers>
  <buildWrappers/>
</project>
"""


jobs = {
    # Polls the repo every minute: a push to master starts the whole pipeline
    JOB1: job(
        "Job 1: install and configure the Puppet agent on the test server. "
        "Polls the git repo's master branch every minute and starts the pipeline on a new commit.",
        "test-server",
        script("job1-puppet-agent.sh"),
        scm=git_scm(),
        triggers="""<triggers>
    <hudson.triggers.SCMTrigger><spec>* * * * *</spec><ignorePostCommitHooks>false</ignorePostCommitHooks></hudson.triggers.SCMTrigger>
  </triggers>""",
        publishers=trigger_next(JOB2),
    ),
    JOB2: job(
        "Job 2: push the Ansible configuration that installs Docker on the test server.",
        "built-in",
        script("job2-ansible-docker.sh"),
        publishers=trigger_next(JOB3),
    ),
    JOB3: job(
        "Job 3: build the PHP website image from the git repo's Dockerfile and deploy it on the test server. "
        "If it fails, a post-build task deletes the running container.",
        "test-server",
        script("job3-build-deploy.sh"),
        scm=git_scm(),
        properties="""<properties>
    <hudson.model.ParametersDefinitionProperty>
      <parameterDefinitions>
        <hudson.model.BooleanParameterDefinition>
          <name>SIMULATE_FAILURE</name>
          <description>Fail on purpose after deploying, to test that the container is deleted on failure.</description>
          <defaultValue>false</defaultValue>
        </hudson.model.BooleanParameterDefinition>
      </parameterDefinitions>
    </hudson.model.ParametersDefinitionProperty>
  </properties>""",
        # Task 4: runs only when the log shows the shell step failed
        publishers=f"""<hudson.plugins.postbuildtask.PostbuildTask plugin="postbuild-task">
      <tasks>
        <hudson.plugins.postbuildtask.TaskProperties>
          <logTexts>
            <hudson.plugins.postbuildtask.LogProperties>
              <logText>Build step 'Execute shell' marked build as failure</logText>
              <operator>AND</operator>
            </hudson.plugins.postbuildtask.LogProperties>
          </logTexts>
          <EscalateStatus>false</EscalateStatus>
          <RunIfJobSuccessful>false</RunIfJobSuccessful>
          <script>{script("job3-on-failure.sh")}</script>
        </hudson.plugins.postbuildtask.TaskProperties>
      </tasks>
    </hudson.plugins.postbuildtask.PostbuildTask>""",
    ),
}

VIEW = f"""<?xml version="1.1" encoding="UTF-8"?>
<au.com.centrumsystems.hudson.plugin.buildpipeline.BuildPipelineView plugin="build-pipeline-plugin">
  <name>Project1-Pipeline</name>
  <description>{JOB1} -&gt; {JOB2} -&gt; {JOB3}</description>
  <filterExecutors>false</filterExecutors>
  <filterQueue>false</filterQueue>
  <properties class="linked-list"/>
  <selectedJob>{JOB1}</selectedJob>
  <refreshFrequency>3</refreshFrequency>
  <showPipelineHeader>true</showPipelineHeader>
  <showPipelineDefinitionHeader>true</showPipelineDefinitionHeader>
  <noOfDisplayedBuilds>5</noOfDisplayedBuilds>
  <buildViewTitle></buildViewTitle>
  <consoleOutputLinkStyle>Lightbox</consoleOutputLinkStyle>
</au.com.centrumsystems.hudson.plugin.buildpipeline.BuildPipelineView>
"""

out = HERE / "jobs"
out.mkdir(exist_ok=True)
for name, xml in jobs.items():
    (out / f"{name}.xml").write_text(xml)
(out / "Project1-Pipeline.view.xml").write_text(VIEW)
print("wrote", ", ".join(sorted(p.name for p in out.glob("*.xml"))))
