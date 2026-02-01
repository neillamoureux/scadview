# Code of Conduct

## Our Pledge

We as members, contributors, and maintainers pledge to make participation in this
community a harassment-free experience for everyone, regardless of age, body
size, visible or invisible disability, ethnicity, sex characteristics, gender
identity and expression, level of experience, education, socio-economic status,
nationality, personal appearance, race, religion, or sexual identity and
orientation.

We pledge to act and interact in ways that contribute to an open, welcoming,
diverse, inclusive, and healthy community.

## Our Standards

Examples of behavior that contributes to a positive environment include:

- Demonstrating empathy and kindness toward other people
- Being respectful of differing opinions, viewpoints, and experiences
- Giving and gracefully accepting constructive feedback
- Accepting responsibility and apologizing to those affected by our mistakes
- Focusing on what is best for the project and its users

Examples of unacceptable behavior include:

- The use of sexualized language or imagery, and sexual attention or advances
- Trolling, insulting or derogatory comments, and personal or political attacks
- Public or private harassment
- Publishing others’ private information without explicit permission
- Other conduct that could reasonably be considered inappropriate in a
  professional or collaborative engineering setting

## Enforcement Responsibilities

Project maintainers are responsible for clarifying and enforcing our standards of
acceptable behavior and will take appropriate and fair corrective action in
response to any behavior they deem inappropriate, threatening, offensive, or
harmful.

Maintainers have the right and responsibility to remove, edit, or reject
comments, commits, code, issues, and other contributions that are not aligned
with this Code of Conduct.

## Scope

This Code of Conduct applies within all project spaces, including:

- GitHub issues, pull requests, and code reviews
- Discussions, documentation, and design proposals
- Community forums and chats
- Public spaces when representing the project

## Reporting & Enforcement

Instances of abusive, harassing, or otherwise unacceptable behavior may be
reported confidentially to the project maintainer at:

**neil.lamoureux+scadview@gmail.com**

All reports will be reviewed promptly and fairly. Privacy and confidentiality
will be respected to the extent possible.

---

# Engineering Norms (Project-Specific Addendum)

This project operates in the domain of **CAD, mesh processing, CSG, geometry,
rendering, and numerical computation**. These areas often involve strong
technical opinions and trade-offs. The following norms exist to keep technical
discussion productive and respectful.

This section does **not** replace the Code of Conduct above — it clarifies how it
applies in an engineering-heavy context.

## Design and Architecture Discussions

- Prefer **questions over declarations**  
  (“What constraints led to this approach?” beats “This is the wrong design.”)

- Acknowledge trade-offs explicitly  
  Geometry kernels, mesh libraries, and rendering pipelines all involve
  compromises between correctness, performance, robustness, portability, and
  complexity.

- Avoid absolutist language  
  Phrases like *“obviously,” “any competent implementation,”* or *“this is
  trivial”* are rarely accurate and often alienating.

## Code Review Etiquette

- Critique **code and design**, not the contributor  
  Comments should address *what* and *why*, never *who*.

- Be precise and actionable  
  “This is inefficient” is less helpful than “This creates O(n²) behavior for
  large meshes; here’s an alternative.”

- Respect scope and intent  
  Pull requests should be reviewed against their stated goals, not expanded into
  unrelated redesigns unless invited.

- Maintain a professional tone, even in disagreement  
  Strong technical disagreement is acceptable; dismissiveness is not.

## Performance and Correctness Discussions

- Performance concerns should be **measured or motivated**, not speculative  
  If you claim a bottleneck, explain the workload or scenario where it matters.

- Numerical robustness is complex  
  Floating-point precision, tolerances, manifold assumptions, and degenerate
  geometry are hard problems. Assume good faith when different approaches are
  taken.

- Avoid “purity tests”  
  The project may prioritize usability, debuggability, or portability over
  maximal theoretical elegance.

## Geometry, CAD, and CSG-Specific Norms

- There are often **multiple valid representations** of the same shape  
  Meshes, B-reps, implicit solids, and hybrid approaches each have legitimate
  use cases.

- “Correctness” depends on context  
  A solution appropriate for manufacturing, visualization, or teaching may not
  be identical.

- Library and dependency choices are contextual  
  Decisions may be driven by platform support, licensing, stability, or
  ecosystem compatibility.

## Disagreements and Escalation

If a technical discussion becomes heated or unproductive:

- Pause and restate the shared goal
- Narrow the discussion to a specific, concrete issue
- Defer or move the discussion to a separate issue if needed
- Maintainers may step in to refocus or conclude the discussion

Repeated failure to follow these norms may be treated as a Code of Conduct
violation.

---

## Attribution

This Code of Conduct is adapted from the Contributor Covenant, version 2.1:
https://www.contributor-covenant.org/version/2/1/code_of_conduct.html
