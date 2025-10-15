pipeline {
    agent {
        docker {
            image 'python3.10' // Specifies the Docker image to use (e.g., Python 3.9)
            args '-u root' // Optional: Runs the container as root user
        }
        
    }
    stages {
        stage('Checkout') {
            steps {
                checkout scm
            }
        }
        stage('Run Python Script') {
            steps {
                sh 'python migration.py' // Executes your Python script
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
