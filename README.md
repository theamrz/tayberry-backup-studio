# Tayberry Backup Studio - Liquid Glass Edition 🌌

[Tayberry Backup Studio](app/resources/logo.png)

## Overview

**Tayberry Backup Studio (Liquid Edition)** is a next-generation backup management interface designed with a focus on modern aesthetics, fluid user experience, and robust functionality. Built using **Python 3.9+** and **PyQt6**, it features a fully custom-painted UI engine that renders real-time glassmorphism, particle simulations, and advanced gradient composites.

### Key Features 🚀

-   **Liquid Glass UI Engine**: A custom rendering pipeline using `QPainter` for real-time blur, noise, and light diffusion.
-   **Galaxy Particle Simulation**: Interactive background with parallax starfields and nebulae.
-   **Smart Backup & Diff**: Integrated tools for project state comparison ("Diff Check") and secure data archiving ("Write Backup").
-   **Cross-Platform**: Optimized for macOS (with native .app/.dmg support) and Windows.
-   **Fluid Controls**: Custom-built input fields and buttons with animated state transitions.

## Installation 🛠️

### Prerequisites

-   Python 3.9 or higher
-   PyQt6

### Quick Start

1.  **Clone the Repository**
    ```bash
    git clone https://github.com/theamrz/tayberry-backup-studio.git
    cd tayberry-backup-studio
    ```

2.  **Install Dependencies**
    ```bash
    pip install -r requirements.txt
    ```

3.  **Run the Application**
    ```bash
    python3 -m app.main
    ```

## Building for macOS 🍎

To create a standalone `.app` bundle and `.dmg` installer:

```bash
python3 build_mac_app.py
```
This will generate `Liquid Glass Demo.app` in the `dist/` directory and a mountable `LiquidGlassDemo.dmg` in the project root.

## Architecture 🏗️

The application uses a component-based architecture:
-   **`GlassSurface`**: Core widget handling frosted glass effects using `QGraphicsEffect` and painter composition.
-   **`GalaxyBackground`**: Handles the infinite loop animation loop for the background particles.
-   **`LiquidWindow`**: The central orchestrator managing layout and state.

## License

Copyright © 2026 **Amirhosein Rezapour** (Techili / Tayberry). All rights reserved.
Startups and Enterprise solutions by [Techili.ir](https://techili.ir).
