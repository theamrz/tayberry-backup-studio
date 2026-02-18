# TBcms Liquid Glass Demo

A high-performance PyQt6 desktop application showcasing "Liquid Glass" UI design.
This project implements advanced UI rendering techniques including blurred glass, galaxy particle simulations, and fluid refractive interfaces, all within a standard Python desktop environment.

**Author:** Amirhosein Rezapour
**Web:** [techili.ir](https://techili.ir) | [tayberry.ir](https://tayberry.ir) | [tayberry.dev](https://tayberry.dev)

## Features

- **Galaxy Background**: Animated particle simulation with nebulae and parallax depth.
- **Liquid Glass Surface**: Real-time background blur, frost, and edge lighting effects.
- **Fluid Interactions**: Elastic mouse tracking and hover states.
- **Star Border**: Custom animated gradient borders.
- **Adaptive Performance**: Automatic quality adjustments based on frame rate.

## Requirements

- Python 3.11+
- PyQt6
- numpy (for fast particle math)
- Pillow (for texture generation)

## Installation

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/yourusername/liquid-glass-demo.git
    cd liquid-glass-demo
    ```

2.  **Create a virtual environment (recommended):**
    ```bash
    python3 -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    ```

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

## Usage

Run the application:

```bash
python -m app.main
```

## Performance Controls

The application includes a floating control pill to tweak rendering parameters:
- **Blur**: Adjust the strength of the glass blur effect.
- **Refraction**: Control the liquid distortion strength.
- **Frost**: Add noise/grain to the glass.
- **Performance Mode**: Switch between CPU/GPU render paths (if available).

## License

MIT License. See LICENSE for details.
