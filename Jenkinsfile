// Declarative pipeline for the Sanders and Fresco web app.
// Stages map to the five jobs in the assignment: Compile, Code Review,
// Unit test, Package and Deploy.
pipeline {
    agent any

    tools {
        maven 'Maven-3.9'
        jdk 'JDK-17'
    }

    environment {
        TOMCAT_URL = 'http://localhost:8080'
        APP_CONTEXT = '/sf-webapp'
    }

    options {
        timestamps()
        buildDiscarder(logRotator(numToKeepStr: '10'))
    }

    stages {
        stage('Compile') {
            steps {
                sh 'mvn -B clean compile'
            }
        }

        stage('Code Review') {
            steps {
                sh 'mvn -B checkstyle:check'
            }
        }

        stage('Unit test') {
            steps {
                sh 'mvn -B test'
            }
            post {
                always {
                    junit allowEmptyResults: true, testResults: 'target/surefire-reports/*.xml'
                }
            }
        }

        stage('Package') {
            steps {
                sh 'mvn -B -DskipTests package'
            }
            post {
                success {
                    archiveArtifacts artifacts: 'target/*.war', fingerprint: true
                }
            }
        }

        stage('Deploy') {
            steps {
                // Tomcat credentials with the manager-script role, stored in Jenkins
                withCredentials([usernamePassword(credentialsId: 'tomcat-deployer',
                                                  usernameVariable: 'TOMCAT_USER',
                                                  passwordVariable: 'TOMCAT_PASS')]) {
                    sh '''
                        curl -sf -u "$TOMCAT_USER:$TOMCAT_PASS" \
                          -T target/sf-webapp.war \
                          "$TOMCAT_URL/manager/text/deploy?path=$APP_CONTEXT&update=true"
                    '''
                }
            }
        }
    }

    post {
        failure {
            echo 'Build failed. Check the stage logs above.'
        }
    }
}
