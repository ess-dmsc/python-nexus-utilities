@Library('ecdc-pipeline')
import ecdcpipeline.ContainerBuildNode
import ecdcpipeline.PipelineBuilder

project = "python-nexus-utilities"

container_build_nodes = [
  'centos7': ContainerBuildNode.getDefaultContainerBuildNode('centos7-gcc8')
]

pipeline_builder = new PipelineBuilder(this, container_build_nodes)
pipeline_builder.activateEmailFailureNotifications()

builders = pipeline_builder.createBuilders { container ->
  pipeline_builder.stage("${container.key}: Checkout") {
    dir(pipeline_builder.project) {
      scm_vars = checkout scm
    }
    container.copyTo(pipeline_builder.project, pipeline_builder.project)
  }  // stage

  pipeline_builder.stage("${container.key}: Dependencies") {
    def conan_remote = "ess-dmsc-local"
    container.sh """
      cd ${project}
      python3.6 -m venv venv
      venv/bin/pip --proxy ${http_proxy} install -r requirements.txt
    """
  } // stage

  pipeline_builder.stage("${container.key}: Formatting (black) ") {
    def conan_remote = "ess-dmsc-local"
    container.sh """
      cd ${project}
      venv/bin/python -m black --check .
    """
  } // stage

//   pipeline_builder.stage("${container.key}: Static Analysis (flake8) ") {
//     def conan_remote = "ess-dmsc-local"
//     container.sh """
//       cd ${project}
//       venv/bin/python -m flake8
//     """
//   } // stage

  pipeline_builder.stage("${container.key}: Test") {
    def test_output = "TestResults.xml"
    container.sh """
      cd ${project}
      venv/bin/python -m pytest --junitxml=${test_output} --ignore=venv
    """
    container.copyFrom("${project}/${test_output}", ".")
    xunit thresholds: [failed(unstableThreshold: '0')], tools: [JUnit(deleteOutputFiles: true, pattern: '*.xml', skipNoTestFiles: false, stopProcessingIfError: true)]
  } // stage
}  // createBuilders

node {
  dir("${project}") {
    scm_vars = checkout scm
  }

  try {
    parallel builders
  } catch (e) {
    throw e
  }

  // Delete workspace when build is done
  cleanWs()
}
