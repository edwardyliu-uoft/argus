"""Argus Programmatic API.

This module will provide a programmatic API for using Argus as a library
rather than through the command-line interface.

Planned Features:
-----------------

1. Programmatic Analysis:
   - Run analysis from Python code
   - Configure analysis options programmatically
   - Access results as Python objects

   Example:
   ```python
   from argus.core.api import analyze_project
   
   result = await analyze_project(
       project_path="/path/to/project",
       config={"orchestrator": {"llm": "gemini"}}
   )
   
   print(f"Found {len(result.findings)} vulnerabilities")
   for finding in result.findings:
       print(f"  {finding.severity}: {finding.title}")
   ```

2. Incremental Analysis:
   - Analyze specific contracts
   - Re-run specific phases
   - Update existing reports

   Example:
   ```python
   from argus.core.api import analyze_contract
   
   result = await analyze_contract(
       contract_path="contracts/MyContract.sol",
       phases=["semantic", "static"]
   )
   ```

3. Custom Workflows:
   - Build custom analysis pipelines
   - Integrate with CI/CD systems
   - Extend with custom checks

   Example:
   ```python
   from argus.core.api import create_orchestrator
   
   orchestrator = create_orchestrator(project_path)
   orchestrator.add_custom_phase(my_custom_check)
   result = await orchestrator.run()
   ```

4. Result Processing:
   - Query findings programmatically
   - Export to various formats
   - Generate custom reports

   Example:
   ```python
   from argus.core.api import load_report
   
   report = load_report("argus/20241211_100000/raw-analysis-data.json")
   critical = report.findings.filter(severity="critical")
   report.export(format="csv", output="findings.csv")
   ```

Status:
-------
This API is currently under development. For now, please use the CLI:

    argus analyze /path/to/project

See README.md for full CLI documentation.

Contributing:
-------------
If you'd like to contribute to the API development, please see CONTRIBUTING.md
and join the discussion in GitHub Issues.
"""

# TODO: Implement programmatic API
# See docstring above for planned features