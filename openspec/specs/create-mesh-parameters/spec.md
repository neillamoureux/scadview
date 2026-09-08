# create-mesh-parameters Specification

## Purpose

Expose safe, defaulted `create_mesh` inputs as interactive controls so users can
explore parameterized geometry without editing the Python module.

## Requirements

### Requirement: Discover supported create_mesh parameters

SCADview SHALL discover parameters from the loaded module's `create_mesh`
signature in the isolated module-loading environment. An ordinary named or
keyword-only parameter SHALL be eligible for a control when it has a default
value whose exact built-in type is one of `bool`, `int`, `float`, or `str`.
`None`, mutable values, enums, paths, NumPy scalars, custom subclasses,
positional-only parameters, and variadic parameters SHALL not be exposed.
Parameters SHALL be reported in signature order with their names, scalar types,
and default values.

#### Scenario: Module defines a supported defaulted parameter

- **WHEN** a module defines `create_mesh(width: float = 2.5)` and is loaded
- **THEN** SCADview reports a parameter named `width` with type `float` and default value `2.5`

#### Scenario: Module has no supported parameters

- **WHEN** a module defines `create_mesh()` or only parameters outside the supported defaulted scalar contract
- **THEN** SCADview loads the module using its existing behavior and displays no parameter controls

#### Scenario: Module has a required parameter

- **WHEN** a module defines a required `create_mesh` parameter
- **THEN** SCADview reports the existing load error rather than inventing a value or prompting for an unsupported required input

### Requirement: Display parameter controls

SCADview SHALL display one labeled control for each discovered supported
parameter, initialized to its reported default or current session value. The
control type SHALL preserve the parameter's scalar type when converting user
input into a value sent to `create_mesh`. Boolean parameters SHALL use a
checkbox that emits an actual `bool` value rather than parsing arbitrary text.

#### Scenario: Parameter controls appear after loading

- **WHEN** a module with supported parameters completes a load
- **THEN** the UI displays controls labeled with the parameter names and values initialized from the module defaults

#### Scenario: Parameter metadata changes after loading another module

- **WHEN** the user loads a different module
- **THEN** the previous module's parameter controls are removed and replaced by controls for the newly discovered parameters

#### Scenario: Execution fails after parameter discovery

- **WHEN** signature discovery succeeds but `create_mesh` raises an error while building the mesh
- **THEN** SCADview displays the load error while retaining the discovered parameter controls and their last accepted values

#### Scenario: Reset restores loaded-module defaults

- **WHEN** the user changes one or more parameter values and activates Reset Parameters
- **THEN** the controls return to the defaults discovered from the currently loaded `create_mesh` signature

### Requirement: Reset parameter values

SCADview SHALL provide a Reset Parameters control when the loaded module has
supported parameters. Activating it SHALL restore every accepted parameter value
to the corresponding default from the current parameter metadata and SHALL
rebuild the mesh when any value changed. Activating it when all values already
equal their defaults SHALL not enqueue a load request.

#### Scenario: Reset changed values

- **WHEN** the user activates Reset Parameters after changing an accepted value
- **THEN** SCADview restores the discovered default and rebuilds the mesh once

#### Scenario: Reset already-default values

- **WHEN** the user activates Reset Parameters while every value equals its discovered default
- **THEN** SCADview does not enqueue a load request

### Requirement: Rebuild geometry from changed parameters

SCADview SHALL invoke `create_mesh` with the current parameter values whenever a
valid parameter control value changes. Parameter values crossing the loader
process boundary SHALL be simple serializable scalar data.

#### Scenario: User changes a numeric parameter

- **WHEN** the user changes `width` from `2.5` to `3.75` and commits a valid value
- **THEN** SCADview rebuilds the module using `create_mesh(width=3.75)` and displays the resulting mesh

#### Scenario: User enters an invalid value

- **WHEN** the user commits a value that cannot be converted to the parameter's declared scalar type
- **THEN** SCADview reports the validation error, keeps the last valid value, and does not enqueue a mesh rebuild for the invalid value

### Requirement: Preserve parameter state within a module session

SCADview SHALL preserve valid user-selected parameter values when feature state
or debug visualization changes cause the current module to reload. Loading a
different module SHALL initialize its controls from that module's defaults.

#### Scenario: Feature toggle reloads the current module

- **WHEN** the user changes a feature after setting `width` to `3.75`
- **THEN** the feature reload uses `width=3.75` rather than resetting to `2.5`

#### Scenario: Different module is loaded

- **WHEN** the user loads a different module defining a parameter with the same name but a different default
- **THEN** the new module's control starts at its own default value

#### Scenario: Source edit preserves compatible parameters

- **WHEN** the active module is reloaded from the same normalized absolute path and a parameter keeps the same name and supported scalar type
- **THEN** SCADview preserves that parameter's accepted value

#### Scenario: Source edit reconciles incompatible parameters

- **WHEN** the active module is reloaded from the same normalized absolute path and a parameter is added, removed, renamed, or changes supported scalar type
- **THEN** added or changed parameters use their new defaults, and removed or renamed parameters are no longer sent to `create_mesh`

#### Scenario: Equivalent module paths identify one module

- **WHEN** the same module is reloaded through equivalent relative and absolute paths
- **THEN** SCADview normalizes the paths before deciding whether to preserve parameter values

### Requirement: Ignore stale load results

SCADview SHALL associate load results with the parameter and feature state that
requested them and SHALL ignore results from superseded load requests before
updating controller state, controls, load status, or the renderer. The UI SHALL
only stop polling or display an error for the current request generation.

#### Scenario: User changes parameters before an earlier build finishes

- **WHEN** a build for an older parameter value completes after a newer build was requested
- **THEN** SCADview does not display the older mesh or use its metadata to replace the newer request's state

#### Scenario: Stale result arrives after a newer request

- **WHEN** a stale success, error, or completion result arrives after a newer request has been issued
- **THEN** the controller returns a no-op result for the stale result and the UI does not mutate its renderer, controls, error state, or polling timer
