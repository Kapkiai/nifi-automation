pipeline {
    parameters {
      choice(name: 'REGISTRY_ENV', description: 'Registry Enviroment', choices: 'DEV\nSTG\nPRD')
      choice(name: 'NIFI_ENV', description: 'NIFI Enviroment', choices: 'DEV\nSTG\nPRD')
      choice(name: 'PROCESS_GROUP', description: 'PROCESS GROUPS TO AUTOMATE', choices: 'DEV\nSTG\nPRD')
  }
    agent {
        docker {
            image 'python:3.10' // Specifies the Docker image to use (e.g., Python 3.9)
            args '-u root' // Optional: Runs the container as root user
        }
        
    }
    stages {
        stage('Checkout') {
            steps {
                checkout scm
            }
        }
        stage('Instll dependencies') {
            steps {
                sh 'pip install -r requirements.txt' // Executes your Python script
            }
        }
        stage('Echo parameters') {
            steps {
                echo "${parameters.PROCESS_GROUP} - ${process_groups}"
            }
        }
        stage('Run Python Script') {
            steps {
                sh 'python migration.py ${process_groups}' // Executes your Python script
            }
        }
        stage('Run Tests') {
            steps {
                echo 'pytest' // Example: Runs tests using pytest (assuming it's installed)
            }
        }
    }
    post {
        always {
            // Actions to perform regardless of the build result
            echo 'Pipeline finished.'
        }
        success {
            // Actions to perform on successful build
            echo 'Build successful!'
        }
        failure {
            // Actions to perform on build failure
            echo 'Build failed!'
        }
    }
}
