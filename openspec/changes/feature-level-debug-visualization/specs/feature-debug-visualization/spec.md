## Purpose

Allow users to inspect the source geometry associated with named features without changing their model script or conflating visualization with feature inclusion.

## ADDED Requirements

### Requirement: Feature debug mode is independently controlled
The application SHALL provide a global, session-persistent Debug features
visualization toggle that is independent of each feature's enabled/disabled state
and is disabled by default. Changing the toggle after a module is loaded SHALL
request a reload without changing feature enabled state.

#### Scenario: Debug mode is disabled by default
- **WHEN** the application starts
- **THEN** feature source geometry is not visualized unless the user enables Debug features

#### Scenario: Toggling debug mode preserves feature states
- **WHEN** the user enables or disables Debug features
- **THEN** the enabled/disabled state of every named feature remains unchanged

#### Scenario: Debug mode persists for the application session
- **WHEN** the user changes Debug features and then reloads or loads a different module
- **THEN** the selected Debug features state is retained
- **AND THEN** feature discovery for the new module does not reset that state

#### Scenario: Toggling debug mode reloads the current module
- **WHEN** a module is loaded and the user changes Debug features
- **THEN** the application requests a reload using the unchanged feature states and
  the newly selected debug mode

### Requirement: Enabled feature source geometry is visualized
When Debug features is enabled, the application SHALL visualize the source geometry registered for each enabled named feature as separate translucent debug geometry with automatically selected colors. The diagnostic list SHALL replace, rather than overlay, the normal result.

#### Scenario: A feature is registered and enabled
- **WHEN** a named feature registers source geometry and Debug features is enabled
- **THEN** that source geometry is included in the debug visualization

#### Scenario: A feature is disabled
- **WHEN** a named feature is disabled and Debug features is enabled
- **THEN** its source geometry is omitted from the debug visualization

#### Scenario: A subtractive feature is debugged
- **WHEN** an enabled feature is used as a subtractive or tool volume
- **THEN** its captured source geometry is visualized as a debug volume, regardless of whether it contributes triangles to the final model

### Requirement: Source registration semantics are preserved
The application SHALL capture feature source geometry at registration time, preserve registration order, and preserve duplicate registrations of the same feature name as separate debug geometry.

#### Scenario: A feature is transformed through boolean composition
- **WHEN** registered feature geometry is combined with other geometry
- **THEN** Debug features visualizes the registered source geometry rather than attempting to infer feature identity from the composed result

#### Scenario: A feature name is registered more than once
- **WHEN** the same feature name registers multiple source meshes during one load
- **THEN** each registered source mesh is represented separately in debug visualization in registration order

### Requirement: Debug mode follows progressive loading
The application SHALL produce feature-debug visualization for every yielded mesh
result during a progressive module load. For each result, the visualization SHALL
use the ordered enabled-source snapshot registered by that point in the module
execution.

#### Scenario: A module yields multiple mesh results
- **WHEN** Debug features is enabled while the module yields successive results
- **THEN** each result is represented by the enabled feature source geometry captured
  before that yield
- **AND THEN** later registrations do not appear in earlier yielded results

#### Scenario: No feature source geometry is registered
- **WHEN** Debug features is enabled but the module registers no features
- **THEN** the normal result representation remains visible instead of an empty
  feature-debug list

### Requirement: Normal loading remains unchanged when debug mode is off
The application SHALL preserve existing final-mesh behavior, feature filtering, export eligibility, and rendering when Debug features is disabled.

#### Scenario: A normal load completes
- **WHEN** Debug features is disabled and a module produces a final mesh
- **THEN** the final mesh is rendered using the existing normal load behavior

#### Scenario: A debug view is active
- **WHEN** the current load is showing feature debug geometry
- **THEN** the diagnostic geometry is treated as debug output and is not treated as the exportable final model

### Requirement: Feature debug usage is documented with the existing feature example
The project SHALL extend `examples/features.py` and its rendered documentation with
a Debug features usage walkthrough. The walkthrough SHALL use the example's named
subtractive `cable_cutout` tool volume to explain that Debug features visualizes
source/tool geometry, and that the global visualization toggle is independent of
each feature's enabled or disabled state.

#### Scenario: A user follows the feature example walkthrough
- **WHEN** a user loads `examples/features.py` and enables Debug features
- **THEN** the documentation explains that the subtractive `cable_cutout` source is
  visualized as a tool volume while it is enabled
- **AND THEN** it explains that disabling `cable_cutout` omits it from the debug
  view without changing the Debug features toggle
