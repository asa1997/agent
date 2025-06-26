import os
from crewai import Agent, Task, Crew
from crewai_tools import SerperDevTool, FileWriterTool, FileReadTool

# Set up API keys (you'll need to get these)
# os.environ["SERPER_API_KEY"] = "your_serper_api_key"  # Get from serper.dev
# os.environ["OPENAI_API_KEY"] = "your_openai_api_key"  # Get from OpenAI

# Initialize tools
web_search_tool = SerperDevTool()
file_writer_tool = FileWriterTool()
file_read_tool = FileReadTool()

# First, let's create an example environment script template
example_script_content = '''#!/bin/bash
function __besman_install {
    local container
    __besman_check_vcs_exist || return 1 # Checks if GitHub CLI is present or not.
    __besman_check_github_id || return 1 # checks whether the user github id has been populated or not under BESMAN_USER_NAMESPACE
    __besman_echo_white "==> Installing assessment environment..."

    # Ensure Docker
    if ! command -v docker &>/dev/null; then
        __besman_echo_white "Installing Docker..."
        sudo apt update && sudo apt install -y ca-certificates curl software-properties-common
        curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo apt-key add -
        sudo add-apt-repository -y "deb [arch=amd64] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable"
        sudo apt update
        sudo apt install -y docker-ce docker-ce-cli containerd.io
        sudo usermod -aG docker $USER && newgrp docker
    else
        __besman_echo_white "Docker already installed."
    fi

    # Ensure snapd
    if ! command -v snap &>/dev/null; then
        __besman_echo_white "Installing snapd..."
        sudo apt update && sudo apt install -y snapd
    else
        __besman_echo_white "snapd already installed."
    fi

    # Ensure Go
    if ! command -v go &>/dev/null; then
        __besman_echo_white "Installing Go..."
        sudo snap install go --classic
        echo "export PATH=\$PATH:$HOME/go/bin" >> ~/.bashrc
        source ~/.bashrc
    else
        __besman_echo_white "Go already installed."
    fi

    # Install each assessment tool
    IFS=',' read -r -a tools <<<"$BESMAN_ASSESSMENT_TOOLS"
    for t in "${tools[@]}"; do
        case $t in
        scorecard)
            __besman_echo_white "Downloading scorecard from $BESMAN_SCORECARD_ASSET_URL"
            curl -L -o "$HOME/scorecard_5.1.1_linux_amd64.tar.gz" "$BESMAN_SCORECARD_ASSET_URL"
            tar -xzf "$HOME/scorecard_5.1.1_linux_amd64.tar.gz"
            chmod +x "$HOME/scorecard"
            sudo mv "$HOME/scorecard" /usr/local/bin/
            [[ -f "$HOME/scorecard_5.1.1_linux_amd64.tar.gz" ]] && rm "$HOME/scorecard_5.1.1_linux_amd64.tar.gz"
            [[ -z $(which scorecard) ]] && __besman_echo_error "Scorecard installation failed." && return 1
            ;;
        criticality_score)
            __besman_echo_white "Installing Criticality Score CLI..."
            go install github.com/ossf/criticality_score/v2/cmd/criticality_score@latest
            [[ -z $(which criticality_score) ]] && __besman_echo_error "criticality_score installation failed." && return 1
            ;;
        sonarqube)
            container="sonarqube-$BESMAN_ARTIFACT_NAME"
            __besman_echo_white "Setting up SonarQube container: $container..."
            sudo docker rm -f "$container" 2>/dev/null || true
            sudo docker pull sonarqube:latest
            sudo docker run -d --name "$container" -p "${BESMAN_SONARQUBE_PORT}:9000" sonarqube:latest
            sudo curl -L "$BESMAN_SONAR_SCANNER_ASSET_URL" -o "$BESMAN_TOOL_PATH/sonar-scanner-cli.zip"
            sudo unzip "$BESMAN_TOOL_PATH/sonar-scanner-cli.zip" -d "$BESMAN_TOOL_PATH"
            sudo mv "$BESMAN_TOOL_PATH/sonar-scanner-$BESMAN_SONAR_SCANNER_VERSION-linux-x64" "$BESMAN_TOOL_PATH/sonar-scanner"
            echo "export PATH='$PATH:$BESMAN_TOOL_PATH/sonar-scanner/bin'" >> ~/.bashrc
            source ~/.bashrc
            [[ -z $(which sonar-scanner) ]] && __besman_echo_error "sonar scanner installation failed." && return 1
            ;;
        fossology)
            container="fossology-$BESMAN_ARTIFACT_NAME"
            __besman_echo_white "Setting up Fossology container: $container..."
            sudo docker rm -f $container 2>/dev/null || true
            sudo docker run -d --name $container -p ${BESMAN_FOSSOLOGY_PORT}:80 fossology/fossology:latest
            ;;
        spdx-sbom-generator)
            __besman_echo_white "Downloading SPDX SBOM Generator..."
            sudo curl -L -o "$BESMAN_TOOL_PATH/spdx-sbom-generator.tar.gz" "$BESMAN_SPDX_SBOM_ASSET_URL"
            sudo tar -xzf "$BESMAN_TOOL_PATH/spdx-sbom-generator.tar.gz" -C "$BESMAN_TOOL_PATH"
            ;;
        *)
            __besman_echo_warn "Unknown tool: $t"
            ;;
        esac
    done

    # Clones the source code repo.
    if [[ -d $BESMAN_ARTIFACT_DIR ]]; then
        __besman_echo_white "The clone path already contains dir names $BESMAN_ARTIFACT_NAME"
    else
        __besman_echo_white "Cloning source code repo from $BESMAN_USER_NAMESPACE/$BESMAN_ARTIFACT_NAME"
        __besman_repo_clone "$BESMAN_USER_NAMESPACE" "$BESMAN_ARTIFACT_NAME" "$BESMAN_ARTIFACT_DIR" || return 1
        cd "$BESMAN_ARTIFACT_DIR" && git checkout -b "$BESMAN_ARTIFACT_VERSION"_tavoss "$BESMAN_ARTIFACT_VERSION"
        cd "$HOME"
    fi

    if [[ -d $BESMAN_ASSESSMENT_DATASTORE_DIR ]]; then

        __besman_echo_white "Assessment datastore found at $BESMAN_ASSESSMENT_DATASTORE_DIR"
    else
        __besman_echo_white "Cloning assessment datastore from $BESMAN_USER_NAMESPACE/besecure-assessment-datastore"
        __besman_repo_clone "$BESMAN_USER_NAMESPACE" "besecure-assessment-datastore" "$BESMAN_ASSESSMENT_DATASTORE_DIR" || return 1

    fi
    __besman_echo_white "Installation complete."
}

function __besman_uninstall {
    __besman_echo_white "==> Uninstalling assessment environment..."

    IFS=',' read -r -a tools <<<"$BESMAN_ASSESSMENT_TOOLS"
    for t in "${tools[@]}"; do
        case $t in
        scorecard)
            __besman_echo_white "Removing Scorecard..."
            [[ -f "/usr/local/bin/scorecard" ]] && sudo rm /usr/local/bin/scorecard
            ;;
        criticality_score)
            __besman_echo_white "Uninstalling Criticality Score CLI..."
            [[ -f "$(go env GOPATH)/bin/criticality_score" ]] && rm -f "$(go env GOPATH)/bin/criticality_score"
            ;;
        sonarqube)
            container="sonarqube-$BESMAN_ARTIFACT_NAME"
            __besman_echo_white "Removing SonarQube container: $container..."
            sudo docker rm -f $container || true
            sudo rm -rf "$BESMAN_TOOL_PATH/sonar-scanner-cli.zip"
            sudo rm -rf "$BESMAN_TOOL_PATH/sonar-scanner"
            sudo docker rmi -f sonarqube || true
            ;;
        fossology)
            container="fossology-$BESMAN_ARTIFACT_NAME"
            __besman_echo_white "Removing Fossology container: $container..."
            sudo docker rm -f $container || true
            sudo docker rmi -f fossology/fossology || true
            ;;
        spdx-sbom-generator)
            __besman_echo_white "Removing SPDX SBOM Generator files..."
            sudo rm -f "$BESMAN_TOOL_PATH/spdx-sbom-generator.tar.gz"
            sudo rm -rf "$BESMAN_TOOL_PATH/spdx-sbom-generator"
            ;;
        *)
            __besman_echo_warn "Unknown tool: $t"
            ;;
        esac
    done

    if [[ -d $BESMAN_ARTIFACT_DIR ]]; then
        __besman_echo_white "Removing source code repo at $BESMAN_ARTIFACT_DIR"
        rm -rf "$BESMAN_ARTIFACT_DIR"
    else
        __besman_echo_white "Source code repo not found at $BESMAN_ARTIFACT_DIR, not removing"
    fi
        

    __besman_echo_white "Uninstallation complete."
}

function __besman_update {
    __besman_echo_white "==> Updating assessment tools to the latest available versions..."
    IFS=',' read -r -a tools <<<"$BESMAN_ASSESSMENT_TOOLS"
    for t in "${tools[@]}"; do
        case $t in
        scorecard)
            __besman_echo_white "Updating Scorecard image to stable..."
            curl -L -o "$HOME/scorecard_5.1.1_linux_amd64.tar.gz" "$BESMAN_SCORECARD_ASSET_URL"
            tar -xzf "$HOME/scorecard_5.1.1_linux_amd64.tar.gz"
            chmod +x "$HOME/scorecard"
            sudo mv "$HOME/scorecard" /usr/local/bin/
            [[ -f "$HOME/scorecard_5.1.1_linux_amd64.tar.gz" ]] && rm "$HOME/scorecard_5.1.1_linux_amd64.tar.gz"
            ;;
        criticality_score)
            __besman_echo_white "Updating Criticality Score CLI to latest..."
            go install github.com/ossf/criticality_score/v2/cmd/criticality_score@latest
            ;;
        sonarqube)
            container="sonarqube-$BESMAN_ARTIFACT_NAME"
            __besman_echo_white "Updating SonarQube container to latest..."
            sudo docker pull sonarqube:latest
            sudo docker rm -f $container 2>/dev/null || true
            sudo docker run -d --name $container -p ${BESMAN_SONARQUBE_PORT}:9000 sonarqube:latest
            ;;
        fossology)
            container="fossology-$BESMAN_ARTIFACT_NAME"
            __besman_echo_white "Updating Fossology container to latest..."
            sudo docker pull fossology/fossology:latest
            sudo docker rm -f $container 2>/dev/null || true
            sudo docker run -d --name $container -p ${BESMAN_FOSSOLOGY_PORT}:80 fossology/fossology:latest
            ;;
        spdx-sbom-generator)
            __besman_echo_white "Updating SPDX SBOM Generator to version from URL..."
            sudo curl -L -o "$BESMAN_TOOL_PATH/spdx-sbom-generator-latest.tar.gz" "$BESMAN_SPDX_SBOM_ASSET_URL"
            sudo rm -rf "$BESMAN_TOOL_PATH/spdx-sbom-generator"
            sudo tar -xzf "$BESMAN_TOOL_PATH/spdx-sbom-generator-latest.tar.gz" -C "$BESMAN_TOOL_PATH"
            ;;
        *)
            __besman_echo_warn "Unknown tool: $t"
            ;;
        esac
    done
    __besman_echo_white "Update complete."
}

function __besman_validate {
    __besman_echo_white "==> Validating environment..."
    local status=0

    # Validate Docker
    if ! command -v docker &>/dev/null; then
        __besman_echo_error "Docker not found."
        status=1
    else
        __besman_echo_green "Docker is installed."
        local docker_version
        docker_version=$(sudo docker --version)
        __besman_echo_yellow "$docker_version"
    fi

    # Validate containers
    for svc in sonarqube fossology; do
        name="$svc-$BESMAN_ARTIFACT_NAME"
        if ! sudo docker ps -a -q -f name=$name | grep -q .; then
            __besman_echo_error "Container $name is not running."
            status=1
        else
            __besman_echo_green "Container $name is running."
        fi
    done
    if [[ -z $(which sonar-scanner) ]]; then
        __besman_echo_error "Sonar Scanner CLI not found."
        status=1
    else
        __besman_echo_green "Sonar Scanner CLI is installed."
        local sonar_scanner_version
        sonar_scanner_version=$(sonar-scanner --version | grep "SonarScanner" | awk '{print $5}')
        __besman_echo_yellow "$sonar_scanner_version"
    fi
    if [[ -z $(which criticality_score) ]]; then
        __besman_echo_error "Criticality Score CLI not found."
        status=1
    else
        __besman_echo_green "Criticality Score CLI is installed."
    fi 
        
    # fi[[ -z $(which sonar-scanner) ]] && __besman_echo_error "Sonar Scanner CLI not found." && status=1
    # [[ -z $(which criticality_score) ]] && __besman_echo_error "Criticality Score CLI not found." && status=1
    # Validate Go CLI
    if ! command -v go &>/dev/null; then
        __besman_echo_error "Go not found."
        status=1
    else
        __besman_echo_green "Go is installed."
        local go_version
        go_version=$(go version)
        __besman_echo_yellow "$go_version"
    fi
    
    if [[ -z $(which scorecard) ]] && [[ -z $(which scorecard-cli) ]]; then
        __besman_echo_error "Scorecard CLI not found."
        status=1
    else
        __besman_echo_green "Scorecard CLI is installed."
        local scorecard_version
        scorecard_version=$(scorecard version | grep GitVersion: | awk '{print $2}')
        __besman_echo_yellow "$scorecard_version"
    fi 

 
    # # Validate Criticality Score
    # if ! command -v criticality_score &>/dev/null; then
    #     __besman_echo_error "criticality_score CLI not found."
    #     status=1
    # fi

    if [[ $status -eq 0 ]]; then
        __besman_echo_white "Validation succeeded."
        unset status scorecard_version go_version sonar_scanner_version docker_version

    else
        __besman_echo_error "Validation failed."
        unset status scorecard_version go_version sonar_scanner_version docker_version

        return 1
    fi
}

function __besman_reset {
    __besman_echo_white "==> Resetting environment to default state as defined by configuration..."
    # Remove all installed tools and containers
    __besman_uninstall
    # Re-install tools using current config versions
    __besman_install
    __besman_echo_white "Reset complete."
}

'''

# Write the example script to a file
with open("example_security_environment_setup.sh", "w") as f:
    f.write(example_script_content)

print("📝 Example environment script created: example_security_environment_setup.sh")

# Create specialized agents
security_tools_researcher = Agent(
    role="Security Tools Research Specialist",
    goal="Research and gather comprehensive information about security assessment tools including installation methods, dependencies, and configuration requirements",
    backstory="""You are an expert cybersecurity researcher with deep knowledge of security assessment tools. 
    You specialize in understanding tool dependencies, installation procedures, and system requirements for tools like 
    SonarQube, SPDX-SBOM-Generator, Fossology, Scorecard, and Criticality Score. You stay updated with the latest 
    versions and best practices for security tool deployment.""",
    tools=[web_search_tool],
    llm="ollama/llama3.2:latest",
    verbose=True,
    allow_delegation=False
)

dependency_analyzer = Agent(
    role="Project Dependency Analyzer",
    goal="Analyze project structures and identify dependencies for various programming languages and frameworks",
    backstory="""You are a software architecture expert who specializes in analyzing project dependencies across 
    multiple programming languages including Python, Node.js, Java, Go, Rust, and more. You understand package 
    managers, build systems, and can identify the tools needed to install project dependencies for security assessment.""",
    tools=[web_search_tool],
    llm="ollama/llama3.2:latest",
    verbose=True,
    allow_delegation=False
)

script_template_analyzer = Agent(
    role="Script Template Analyzer",
    goal="Analyze the provided example script template and understand its structure, functions, and best practices",
    backstory="""You are an expert in shell scripting and DevOps automation. You excel at analyzing existing scripts, 
    understanding their architecture, and identifying areas for improvement. You can extract patterns, functions, 
    and best practices from template scripts to create enhanced versions.""",
    tools=[file_read_tool],
    llm="ollama/codellama:7b",
    verbose=True,
    allow_delegation=False
)

shell_script_developer = Agent(
    role="Shell Script Developer",
    goal="Create robust, cross-platform shell scripts based on templates and research, with proper error handling and logging",
    backstory="""You are an experienced DevOps engineer and shell scripting expert. You create production-ready 
    scripts that are maintainable, well-documented, and handle edge cases gracefully. You understand both bash 
    and zsh compatibility, and you write scripts that work across different Linux distributions and macOS. You excel 
    at enhancing existing script templates with new functionality while maintaining their structure and best practices.""",
    tools=[file_writer_tool, file_read_tool],
    llm="ollama/codellama:7b",
    verbose=True,
    allow_delegation=False
)

# Define tasks
analyze_template_script_task = Task(
    description="""Analyze the provided example environment script template located at 'example_security_environment_setup.sh'.

    Your analysis should cover:
    1. Script structure and organization
    2. Function definitions and their purposes
    3. Error handling mechanisms
    4. Logging and output formatting
    5. Command-line argument parsing
    6. System requirement checks
    7. Installation patterns and best practices
    8. Project type detection logic
    9. Dependency installation approaches
    10. Areas that need enhancement or modification

    Understand how the template is organized so that the new script can follow the same structure and patterns while incorporating the researched security tools.""",
    expected_output="""A comprehensive analysis of the template script including:
    - Overview of script structure and key functions
    - Identification of reusable patterns and functions
    - List of areas where security tool installations should be integrated
    - Recommendations for enhancing the template
    - Understanding of the script's architecture for building upon it""",
    agent=script_template_analyzer
)

research_security_tools_task = Task(
    description="""Research the following security assessment tools and gather detailed information:

    1. SonarQube - Static code analysis platform
    2. SPDX-SBOM-Generator - Software Bill of Materials generator
    3. Fossology - License compliance and vulnerability scanning
    4. Scorecard - Security health metrics for open source projects
    5. Criticality Score - Criticality assessment for open source projects

    For each tool, gather:
    - Latest stable version and download URLs
    - System requirements (OS, memory, disk space)
    - Installation methods (package managers, Docker, source compilation)
    - Required dependencies and prerequisites
    - Configuration requirements
    - Default ports and network requirements
    - Common installation issues and solutions
    - Command-line usage examples

    Also research additional security tools that complement these core tools for a comprehensive security assessment environment.

    Focus on finding the exact installation commands and procedures that can be integrated into a shell script.""",
    expected_output="""A comprehensive research report containing:
    - Detailed installation commands for each security tool
    - System requirements and dependencies
    - Step-by-step installation procedures
    - Configuration recommendations
    - Troubleshooting tips
    - List of additional recommended security tools
    - Specific shell commands that can be used in the script""",
    agent=security_tools_researcher
)

analyze_project_dependencies_task = Task(
    description="""Research and analyze how to detect and install project dependencies for security assessment:

    1. Research methods to detect project types and their dependency files:
       - Python: requirements.txt, setup.py, pyproject.toml, Pipfile
       - Node.js: package.json, yarn.lock, package-lock.json
       - Java: pom.xml, build.gradle, build.xml
       - Go: go.mod, go.sum
       - Rust: Cargo.toml, Cargo.lock
       - Ruby: Gemfile, Gemfile.lock
       - PHP: composer.json, composer.lock
       - .NET: *.csproj, packages.config, *.sln
       - C/C++: CMakeLists.txt, Makefile, conanfile.txt

    2. Research installation commands for each package manager:
       - pip, pipenv, poetry (Python)
       - npm, yarn, pnpm (Node.js)
       - maven, gradle (Java)
       - go mod (Go)
       - cargo (Rust)
       - bundler (Ruby)
       - composer (PHP)
       - dotnet, nuget (.NET)
       - cmake, make, conan (C/C++)

    3. Research how to handle virtual environments and containerization
    4. Research dependency vulnerability scanning integration
    5. Find the best practices for dependency installation in security assessment contexts

    Focus on providing exact commands and detection logic that can be implemented in shell script functions.""",
    expected_output="""A detailed analysis containing:
    - Shell script functions to detect different project types
    - Exact commands to install dependencies for each language/framework
    - Virtual environment setup procedures
    - Integration points with security assessment tools
    - Best practices for dependency management in security contexts
    - Error handling approaches for dependency installation""",
    agent=dependency_analyzer
)

generate_enhanced_environment_script_task = Task(
    description="""Create an enhanced security assessment environment setup script based on:
    1. The analyzed template script structure and patterns
    2. The researched security tools installation information
    3. The project dependency analysis and installation methods

    Using the example script template as a foundation, enhance it with:

    1. **Security Tools Integration**: Replace the example tool installations with actual installations for:
       - SonarQube (with proper database setup and configuration)
       - SPDX-SBOM-Generator (with all required dependencies)
       - Fossology (with database and web interface setup)
       - Scorecard (with proper Go environment)
       - Criticality Score (with Python environment)
       - Additional complementary security tools from research

    2. **Enhanced Project Detection**: Improve the detect_project_type function with:
       - More comprehensive file pattern detection
       - Support for additional languages and frameworks
       - Better handling of multi-language projects
       - Detection of containerized projects (Docker, Kubernetes)

    3. **Robust Dependency Installation**: Enhance install_project_dependencies with:
       - Virtual environment management
       - Version conflict resolution
       - Dependency vulnerability scanning
       - Build tool integration
       - Error recovery mechanisms

    4. **Advanced Features**: Add new functions for:
       - Tool version management and updates
       - Configuration file generation
       - Security assessment workflow automation
       - Report generation and aggregation
       - Integration with CI/CD pipelines
       - Backup and restore functionality

    5. **Enhanced Error Handling**: Improve error handling with:
       - Rollback capabilities for failed installations
       - Detailed error reporting and logging
       - Recovery suggestions for common issues
       - Validation checks for each installation step

    6. **Configuration Management**: Add support for:
       - Configuration file templates
       - Environment-specific settings
       - Tool integration configurations
       - Custom security policies

    Maintain the same script structure, function naming conventions, and coding style as the template while significantly expanding its capabilities.""",
    expected_output="""A complete, production-ready shell script file named 'security-assessment-environment-setup.sh' that:
    - Follows the template's structure and coding patterns
    - Includes all researched security tools with proper installation procedures
    - Has comprehensive project type detection and dependency installation
    - Includes advanced error handling and rollback capabilities
    - Supports configuration management and customization
    - Is well-documented with inline comments explaining each enhancement
    - Includes usage examples and comprehensive help documentation
    - Has been tested for common scenarios and edge cases
    - Is ready for production deployment""",
    agent=shell_script_developer,
    context=[analyze_template_script_task, research_security_tools_task, analyze_project_dependencies_task]
)

# Create the crew
security_environment_crew = Crew(
    agents=[script_template_analyzer, security_tools_researcher, dependency_analyzer, shell_script_developer],
    tasks=[analyze_template_script_task, research_security_tools_task, analyze_project_dependencies_task, generate_enhanced_environment_script_task],
    verbose=True,
    planning=True,  # Enable planning for better coordination
    memory=True     # Enable memory for better context retention
)

# Function to run the crew
def setup_security_environment():
    """
    Execute the security environment setup crew to generate the enhanced environment script.
    """
    print("🚀 Starting Security Assessment Environment Setup Crew...")
    print("📋 This crew will:")
    print("   1. Analyze the provided example script template")
    print("   2. Research security tools and their installation methods")
    print("   3. Analyze project dependency management approaches")
    print("   4. Generate an enhanced environment setup script")
    print()
    
    try:
        result = security_environment_crew.kickoff()
        print("\n" + "="*60)
        print("✅ Security Environment Setup Script Generated Successfully!")
        print("="*60)
        print("📄 Generated Files:")
        print("   • example_security_environment_setup.sh (template)")
        print("   • security-assessment-environment-setup.sh (enhanced script)")
        print()
        print("🔧 Next Steps:")
        print("   1. Review the generated script")
        print("   2. Customize configuration as needed")
        print("   3. Test in a safe environment")
        print("   4. Deploy to your security assessment infrastructure")
        print()
        print("📖 Usage:")
        print("   chmod +x security-assessment-environment-setup.sh")
        print("   ./security-assessment-environment-setup.sh --help")
        print("="*60)
        return result
    except Exception as e:
        print(f"❌ Error during crew execution: {str(e)}")
        print("🔍 Check the logs for more details")
        return None

# Additional utility functions
def validate_environment():
    """
    Validate that the required environment is set up correctly.
    """
    required_env_vars = ["SERPER_API_KEY", "OPENAI_API_KEY"]
    missing_vars = []
    
    for var in required_env_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        print("❌ Missing required environment variables:")
        for var in missing_vars:
            print(f"   • {var}")
        print("\n🔧 Please set these environment variables before running the crew:")
        for var in missing_vars:
            print(f"   export {var}='your_api_key_here'")
        return False
    
    print("✅ Environment validation passed")
    return True

def cleanup_files():
    """
    Clean up generated files (useful for testing).
    """
    files_to_remove = [
        "example_security_environment_setup.sh",
        "security-assessment-environment-setup.sh"
    ]
    
    for file in files_to_remove:
        if os.path.exists(file):
            os.remove(file)
            print(f"🗑️  Removed {file}")

def show_crew_info():
    """
    Display information about the crew and its capabilities.
    """
    print("🤖 Security Assessment Environment Setup Crew")
    print("=" * 50)
    print()
    print("👥 Agents:")
    print("   1. Script Template Analyzer")
    print("      • Analyzes the provided example script")
    print("      • Identifies patterns and best practices")
    print("      • Provides architectural guidance")
    print()
    print("   2. Security Tools Research Specialist")
    print("      • Researches latest security tool versions")
    print("      • Finds installation procedures and requirements")
    print("      • Identifies tool dependencies and configurations")
    print()
    print("   3. Project Dependency Analyzer")
    print("      • Analyzes project structures and dependencies")
    print("      • Researches package managers and build tools")
    print("      • Provides dependency installation strategies")
    print()
    print("   4. Shell Script Developer")
    print("      • Creates production-ready shell scripts")
    print("      • Implements error handling and logging")
    print("      • Ensures cross-platform compatibility")
    print()
    print("🛠️  Tools Used:")
    print("   • SerperDevTool - Web search for latest information")
    print("   • FileWriterTool - Generate script files")
    print("   • FileReadTool - Analyze template scripts")
    print()
    print("📦 Security Tools Covered:")
    print("   • SonarQube - Static code analysis")
    print("   • SPDX-SBOM-Generator - Software Bill of Materials")
    print("   • Fossology - License compliance scanning")
    print("   • Scorecard - Security health metrics")
    print("   • Criticality Score - Criticality assessment")
    print("   • Additional complementary tools")
    print()
    print("🔧 Project Types Supported:")
    print("   • Python, Node.js, Java, Go, Rust")
    print("   • Ruby, PHP, .NET, C/C++")
    print("   • Docker and containerized projects")
    print("=" * 50)

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "--info":
            show_crew_info()
            sys.exit(0)
        elif sys.argv[1] == "--cleanup":
            cleanup_files()
            sys.exit(0)
        elif sys.argv[1] == "--validate":
            if validate_environment():
                print("✅ Ready to run the crew!")
            else:
                sys.exit(1)
        elif sys.argv[1] == "--help":
            print("Security Assessment Environment Setup Crew")
            print()
            print("Usage:")
            print("  python security_environment_crew.py [OPTIONS]")
            print()
            print("Options:")
            print("  --help      Show this help message")
            print("  --info      Show detailed crew information")
            print("  --validate  Validate environment setup")
            print("  --cleanup   Remove generated files")
            print()
            print("Examples:")
            print("  python security_environment_crew.py")
            print("  python security_environment_crew.py --validate")
            print("  python security_environment_crew.py --info")
            sys.exit(0)
    
    # Validate environment before running
    if not validate_environment():
        sys.exit(1)
    
    # Run the crew
    setup_security_environment()