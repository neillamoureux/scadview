# SCADview
An application to view 3D meshes created from Python.

## Development
### Requirements:
- Python
- uv
- make

## Versioning
SCADview follows [Semantic Versioning 2.0.0](https://semver.org/).  
In short: MAJOR versions for incompatible API changes, MINOR for backward-compatible
features, and PATCH for backward-compatible bug fixes. While the major version
is 0, we may introduce breaking changes in minor releases.

### Set up
This project uses `make` for commmon tasks. 
- Most of the make commands require that you run `make shell` first.
- To get a list of available commands:
```
make help
```
- To get into the shell:
```
make shell
```
- This will create a virtual python environment if it does not already exist.


---

## 📜 License

SCADview is open-source software licensed under the [Apache License, Version 2.0](LICENSE).

You are free to use, modify, and redistribute this software — including in commercial
applications — provided you include the license text above and retain copyright notices.

---

### ⚠️ Disclaimer

SCADview is provided **“as is”**, without warranty of any kind.
It is intended for visualization, analysis, and experimentation purposes.
It is **not designed for safety-critical, medical, or certified manufacturing applications**.
Use at your own discretion.

---

### 🏷️ Name and Branding

The name **SCADview** and its associated logo are trademarks of **Neil Lamoureux**.  
While you are free to fork and modify the code under the Apache License,  
you **may not use the name SCADview** to promote or distribute modified versions  
without prior written permission.  
Please choose a distinct name for derivative works (e.g. *“YourTool, based on SCADview*).
