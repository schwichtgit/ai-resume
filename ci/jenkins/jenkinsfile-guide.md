# Jenkins Mapping Guide

This guide maps the abstract SDLC principles to Jenkins pipeline configuration.

## Mapping

| Abstract Concept  | Jenkins Equivalent                       |
| ----------------- | ---------------------------------------- |
| Commit gate       | Pipeline stages                          |
| PR gate           | Multibranch pipeline                     |
| Release gate      | Release pipeline / tagged builds         |
| Path filtering    | `changeset` condition in `when` block    |
| Required checks   | Quality Gate plugin / Build status       |
| Branch protection | Bitbucket/GitHub branch rules (external) |

## Skeleton Jenkinsfile

```groovy
pipeline {
    agent any

    tools {
        nodejs 'NodeJS-22'
    }

    stages {
        stage('Install') {
            steps {
                sh 'npm ci'
            }
        }

        stage('Lint') {
            when {
                changeset '**/*.{ts,tsx,js,jsx}'
            }
            steps {
                sh 'npx eslint . --quiet'
            }
        }

        stage('Type Check') {
            when {
                changeset '**/*.{ts,tsx}'
            }
            steps {
                sh 'npx tsc --noEmit'
            }
        }

        stage('Test') {
            steps {
                sh 'npm test'
            }
            post {
                always {
                    junit 'test-results/**/*.xml'
                }
            }
        }

        stage('Build') {
            steps {
                sh 'npm run build'
            }
        }

        stage('Commit Standards') {
            when {
                changeRequest()
            }
            steps {
                script {
                    def commits = sh(
                        script: "git log --format='%s' origin/main..HEAD",
                        returnStdout: true
                    ).trim().split('\n')

                    def pattern = ~/^(feat|fix|docs|style|refactor|perf|test|build|ci|chore|revert)(\(.+\))?: .+/

                    commits.each { msg ->
                        if (!(msg ==~ pattern)) {
                            error "Commit does not match conventional format: ${msg}"
                        }
                    }
                }
            }
        }
    }

    post {
        failure {
            echo 'Pipeline failed.'
        }
        success {
            echo 'All checks passed.'
        }
    }
}
```

## Configuration Notes

- Install the NodeJS plugin for `tools { nodejs }` support
- Configure JUnit test reporter if your test framework supports it
- Use Multibranch Pipeline for automatic PR detection
- Set up Quality Gate plugin for coverage thresholds
