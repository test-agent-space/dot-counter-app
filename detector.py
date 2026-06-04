import numpy as np
import cv2
from PIL import Image
from typing import Tuple, List

def count_dots(
    image_path: str,
    target_color_bgr: Tuple[int, int, int] = (217, 83, 42),
    color_tolerance: int = 15,
    min_area: float = 3.0,
    area_ratio_min: float = 0.5,
    area_ratio_max: float = 2.0,
    circularity_thresh: float = 0.7
) -> Tuple[int, List[np.ndarray], np.ndarray]:
    """
    Detects and counts circular dots of a target color in an image.
    
    Args:
        image_path: Path to the input image.
        target_color_bgr: Target color in BGR format (default: blue-ish dot).
        color_tolerance: Tolerance for Hue in HSV color space (0-179).
        min_area: Absolute minimum area in pixels to be considered a contour (noise floor).
        area_ratio_min: Minimum area as a ratio of the median area of initial contours.
        area_ratio_max: Maximum area as a ratio of the median area of initial contours.
        circularity_thresh: Minimum circularity (4*pi*area/perimeter^2) to be considered a dot.
        
    Returns:
        Tuple of (count, list of valid contour arrays, cleaned binary mask).
    """
    pil_img = Image.open(image_path).convert('RGB')
    img = np.array(pil_img)
    img_bgr = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
    hsv = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2HSV)
    
    target_hsv = cv2.cvtColor(np.uint8([[target_color_bgr]]), cv2.COLOR_BGR2HSV)[0][0]
    
    h_tol = color_tolerance
    # Broad tolerance for Saturation and Value to catch variations in lighting/anti-aliasing
    lower = np.array([
        max(0, target_hsv[0] - h_tol), 
        max(0, target_hsv[1] - 50), 
        max(0, target_hsv[2] - 50)
    ], dtype=np.uint8)
    upper = np.array([
        min(179, target_hsv[0] + h_tol), 
        255, 
        255
    ], dtype=np.uint8)
    
    mask = cv2.inRange(hsv, lower, upper)
    
    # Morphological opening to remove small noise and separate slightly touching dots
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
    mask_clean = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
    
    contours, _ = cv2.findContours(mask_clean, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    # First pass: filter out absolute noise to find the median area of "real" candidates
    initial_areas = [cv2.contourArea(c) for c in contours if cv2.contourArea(c) > min_area]
    
    if not initial_areas:
        return 0, [], mask_clean
        
    median_area = np.median(initial_areas)
    
    # Dynamic area bounds based on the image's own median dot size
    dynamic_area_min = max(min_area, median_area * area_ratio_min)
    dynamic_area_max = min(500, median_area * area_ratio_max) # Cap at 500 to avoid large text blocks
    
    valid_count = 0
    valid_contours = []
    for cnt in contours:
        area = cv2.contourArea(cnt)
        if dynamic_area_min <= area <= dynamic_area_max:
            perimeter = cv2.arcLength(cnt, True)
            if perimeter > 0:
                circularity = 4 * np.pi * area / (perimeter * perimeter)
                if circularity > circularity_thresh:
                    valid_count += 1
                    valid_contours.append(cnt)
                    
    return valid_count, valid_contours, mask_clean

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        path = sys.argv[1]
    else:
        path = "/workspace/sample.png"
    
    # Default target is roughly RGB(42, 83, 217) -> BGR(217, 83, 42)
    count, contours, mask = count_dots(path, target_color_bgr=(217, 83, 42))
    print(f"Counted {count} dots in {path}")
