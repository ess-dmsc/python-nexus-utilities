node('fedora && python3') {
    // Use a virtualenv to prevent polluting the build server
    def installed = fileExists 'bin/activate'
    if (!installed) {
        stage("Install Python Virtual Enviroment") {
            sh 'virtualenv -p python3 --no-site-packages nexus_venv'
        }
    }

    // Get the latest version of the code
    // The 'checkout scm' command will automatically pull down the code from the appropriate branch that triggered this build.
    stage ("Get Latest Code") {
        checkout scm
    }

    // Install dependencies in the virtualenv using pip
    // cd into venv bin and use "python pip" to avoid path length problem
    stage ("Install Application Dependencies") {
        sh '''
            source nexus_venv/bin/activate
            cd nexus_venv/bin
            python pip install -r ../../requirements.txt --proxy=$HTTP_PROXY
            deactivate
           '''
    }

    // Run unit tests
    // python pytest ... is again to avoid path length problems and also to ignore the venv directory
    stage ("Run Unit/Integration Tests") {
        def testsError = null
        try {
            sh '''
                source nexus_venv/bin/activate
                cd nexus_venv/bin
                python pytest ../../ --ignore=../../nexus_venv
                deactivate
               '''
        }
        catch(err) {
            testsError = err
            currentBuild.result = 'FAILURE'
        }
    }
}
