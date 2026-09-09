export function pointerPosition(event, rect, width, height) {
  if (!rect || rect.width <= 0 || rect.height <= 0 || !width || !height) {
    return null;
  }
  return {
    x: ((event.clientX - rect.left) / rect.width) * width,
    y: ((event.clientY - rect.top) / rect.height) * height,
    scale: width / rect.width,
  };
}

export function cropRectangle(start, end, width, height) {
  if (!start || !end || !width || !height) {
    return null;
  }
  const minX = Math.max(Math.min(start.x, end.x), 0);
  const minY = Math.max(Math.min(start.y, end.y), 0);
  const maxX = Math.min(Math.max(start.x, end.x), width);
  const maxY = Math.min(Math.max(start.y, end.y), height);
  return {
    height: Math.round(maxY - minY),
    width: Math.round(maxX - minX),
    x: Math.round(minX),
    y: Math.round(minY),
  };
}

export function isValidCropSelection(selection, minimumSize = 10) {
  return Boolean(selection?.width >= minimumSize && selection?.height >= minimumSize);
}

export function paintMask(maskData, width, height, position, brushSize, falloff) {
  if (!maskData || !width || !height || !position) {
    return;
  }
  const radius = Math.max((brushSize * position.scale) / 2, 1);
  const innerRadius = radius * (1 - falloff);
  const minX = Math.max(Math.floor(position.x - radius), 0);
  const maxX = Math.min(Math.ceil(position.x + radius), width - 1);
  const minY = Math.max(Math.floor(position.y - radius), 0);
  const maxY = Math.min(Math.ceil(position.y + radius), height - 1);
  for (let y = minY; y <= maxY; y += 1) {
    for (let x = minX; x <= maxX; x += 1) {
      const distance = Math.hypot(x - position.x, y - position.y);
      if (distance > radius) {
        continue;
      }
      const intensity =
        distance <= innerRadius
          ? 1
          : 1 - (distance - innerRadius) / Math.max(radius - innerRadius, 1);
      const index = y * width + x;
      maskData[index] = Math.max(maskData[index], intensity);
    }
  }
}

export function invertMask(maskData) {
  if (!maskData) {
    return;
  }
  for (let index = 0; index < maskData.length; index += 1) {
    maskData[index] = 1 - Math.min(Math.max(maskData[index], 0), 1);
  }
}
