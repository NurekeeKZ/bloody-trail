import pygame


class InteractionSystem:
    def nearest(self, position, objects, walls=()):
        candidates = []
        for obj in objects:
            rect = pygame.Rect(obj['rect'])
            near = pygame.Vector2(max(rect.left, min(position[0], rect.right)),
                                  max(rect.top, min(position[1], rect.bottom)))
            distance = pygame.Vector2(position).distance_to(near)
            # Furniture belonging to the target must not occlude itself.
            blocked = any(w != rect and w.clipline(position, near) for w in walls)
            if distance <= 82 and not blocked:
                candidates.append((distance, obj))
        return min(candidates, key=lambda pair: pair[0])[1] if candidates else None
