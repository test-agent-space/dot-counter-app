# Dot Counter App

A cross-platform desktop application for reliably segmenting and counting colored dots in images (e.g., venue seating maps). 

## Features
- **Live Detection**: Upload an image and see the dot count update in real-time.
- **Opacity-Feathered Overlay**: Visually verify detected dots with a continuous opacity slider that fades between the raw image and the processed result.
- **Tunable Parameters**: Adjust color target (via color picker), color tolerance, area bounds, and circularity thresholds to perfectly match your specific images.
- **Cross-Platform**: Native, self-contained builds for Linux, Windows, and macOS.

## Download
Pre-built, self-contained artifacts are available on the [GitHub Releases page](https://github.com/Fishmister42/dot-counter-app/releases). 
*(Note: If the repository is private, ensure you are authenticated with GitHub to download the artifacts.)*

- **macOS**: `dot-counter-macos.zip` (Contains `dot-counter.app`. Right-click -> Open to bypass Gatekeeper if needed).
- **Windows**: `dot-counter-windows.zip` (Extract and run `dot-counter.exe`).
- **Linux**: `dot-counter-linux.tar.gz` (Extract and run `./dot-counter`).

## Detection Approach
The pipeline uses a robust, multi-stage computer vision approach to ensure high accuracy and avoid counting clutter (like text or grayscale artifacts):
1. **Color-Space Masking**: Converts the image to HSV and creates a binary mask based on the target color (with adjustable Hue tolerance, and broad Saturation/Value bounds to handle anti-aliasing).
2. **Morphological Cleaning**: Applies an opening operation to remove small noise and separate slightly touching dots.
3. **Dynamic Size Filtering**: Calculates the median area of initial candidate contours, then filters to keep only contours within a configurable ratio of this median (e.g., 0.5x to 2.0x). This makes the approach generalize well to different image resolutions without hard-coded pixel values.
4. **Circularity Gating**: Computes the circularity ($4\pi \cdot \text{area} / \text{perimeter}^2$) of each candidate. Only shapes exceeding the threshold (default 0.7) are counted as valid dots, effectively rejecting text, lines, and irregular clutter.

*Default parameters are tuned to yield ~1,400 counts on the standard sample venue map, which aligns with the ground-truth estimate.*

## Build from Source

1. **Prerequisites**: Python 3.9 - 3.12
2. **Clone the repository**:
   ```bash
   git clone https://github.com/Fishmister42/dot-counter-app.git
   cd dot-counter-app
   ```
3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```
4. **Run the GUI locally**:
   ```bash
   python app.py
   ```
5. **Build standalone executable** (requires PyInstaller):
   ```bash
   pip install pyinstaller
   pyinstaller --noconfirm --windowed --name dot-counter app.py
   ```
   The resulting executable will be in the `dist/` directory.

## CI/CD
This project uses GitHub Actions to automatically build and package the application for all three major operating systems. Trigger a build by pushing a tag (e.g., `v1.0.0`) or by manually running the "Build and Release" workflow from the Actions tab.
