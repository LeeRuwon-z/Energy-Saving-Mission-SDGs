import heapq
import math
import os
import random
import sys
import asyncio

import pygame


pygame.init()

pygame.display.set_caption("절약 대작전")

WIDTH, HEIGHT = 1000, 680
WORLD_WIDTH, WORLD_HEIGHT = 4300, 3400
FPS = 60
TOP_UI = 90
BOTTOM_UI = 34
VIEW_CENTER = pygame.Vector2(WIDTH // 2, (TOP_UI + HEIGHT - BOTTOM_UI) // 2)

CELL_W, CELL_H = 470, 360
ROOM_W, ROOM_H = 390, 290
MIN_ROOM_W, MIN_ROOM_H = 210, 155
DOOR_SIZE = 68

ROOM_SIZE_UNITS = {
    "living": 10,
    "entry": 3,
    "kitchen": 5,
    "study": 5,
    "master": 6,
    "bed1": 5,
    "bed2": 5,
    "bed3": 5,
    "dress": 2,
    "bath1": 3,
    "bath2": 3,
    "utility": 3,
    "pantry": 2,
    "balcony": 3,
}

screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.SCALED | pygame.FULLSCREEN)
clock = pygame.time.Clock()


COLORS = {
    "outside": (220, 226, 218),
    "ui": (30, 47, 44),
    "ui_2": (49, 76, 69),
    "text": (246, 248, 238),
    "muted": (190, 204, 195),
    "wall": (20, 20, 19),
    "floor_wood": (232, 214, 178),
    "floor_wood_2": (222, 202, 164),
    "floor_tile": (218, 218, 210),
    "floor_tile_2": (203, 207, 205),
    "corridor": (226, 211, 176),
    "wood": (153, 104, 64),
    "wood_dark": (88, 58, 39),
    "green": (75, 179, 103),
    "green_dark": (42, 116, 72),
    "danger": (229, 82, 73),
    "warn": (247, 190, 73),
    "blue": (79, 162, 221),
    "blue_dark": (42, 91, 138),
    "yellow": (255, 231, 91),
    "orange": (244, 133, 66),
    "off": (170, 180, 176),
    "black": (20, 24, 24),
    "white": (255, 255, 255),
    "banana": (247, 218, 70),
}


def load_font(size, bold=False):
    candidates = [
        "C:/Windows/Fonts/malgunbd.ttf" if bold else "C:/Windows/Fonts/malgun.ttf",
        "C:/Windows/Fonts/malgun.ttf",
        "/System/Library/Fonts/AppleSDGothicNeo.ttc",
        "/usr/share/fonts/truetype/nanum/NanumGothic.ttf",
    ]
    for path in candidates:
        if path and os.path.exists(path):
            return pygame.font.Font(path, size)
    return pygame.font.SysFont("malgungothic", size, bold=bold)


FONT_TITLE = load_font(64, True)
FONT_XL = load_font(42, True)
FONT_LG = load_font(28, True)
FONT_MD = load_font(20, True)
FONT_SM = load_font(15)
FONT_XS = load_font(13)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ASSET_DIR = os.path.join(BASE_DIR, "assets")


def draw_text(surface, text, font, color, pos, center=False):
    img = font.render(text, True, color)
    rect = img.get_rect()
    rect.center = pos if center else rect.center
    if center:
        rect.center = pos
    else:
        rect.topleft = pos
    surface.blit(img, rect)
    return rect


def draw_shadow(surface, rect, alpha=48):
    shadow = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
    pygame.draw.ellipse(shadow, (0, 0, 0, alpha), shadow.get_rect())
    surface.blit(shadow, rect.topleft)


def draw_3d_rect(surface, rect, top_color, side_color=None, height=8, radius=5):
    if side_color is None:
        side_color = tuple(max(0, c - 45) for c in top_color)
    side = pygame.Rect(rect.x, rect.y + height, rect.w, rect.h)
    pygame.draw.rect(surface, side_color, side, border_radius=radius)
    pygame.draw.rect(surface, top_color, rect, border_radius=radius)
    pygame.draw.line(surface, side_color, (rect.left, rect.bottom), (rect.right, rect.bottom), 3)


def remove_edge_black_background(surface):
    surface = surface.convert_alpha()
    width, height = surface.get_size()
    stack = [(0, 0), (width - 1, 0), (0, height - 1), (width - 1, height - 1)]
    seen = set()

    def is_bg(x, y):
        r, g, b, a = surface.get_at((x, y))
        return a > 0 and r <= 10 and g <= 10 and b <= 10

    surface.lock()
    while stack:
        x, y = stack.pop()
        if x < 0 or y < 0 or x >= width or y >= height or (x, y) in seen:
            continue
        seen.add((x, y))
        if not is_bg(x, y):
            continue
        surface.set_at((x, y), (0, 0, 0, 0))
        stack.extend(((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)))
    surface.unlock()
    return surface


def crop_to_alpha(surface, padding=3):
    width, height = surface.get_size()
    xs, ys = [], []
    for y in range(height):
        for x in range(width):
            if surface.get_at((x, y)).a > 0:
                xs.append(x)
                ys.append(y)
    if not xs:
        return surface
    rect = pygame.Rect(
        max(0, min(xs) - padding),
        max(0, min(ys) - padding),
        min(width, max(xs) + padding + 1) - max(0, min(xs) - padding),
        min(height, max(ys) + padding + 1) - max(0, min(ys) - padding),
    )
    return surface.subsurface(rect).copy()


def load_sprite(filename, height):
    path = os.path.join(ASSET_DIR, filename)
    try:
        image = pygame.image.load(path).convert_alpha()
    except (pygame.error, FileNotFoundError):
        return None
    image = crop_to_alpha(remove_edge_black_background(image))
    scale = height / image.get_height()
    size = (max(1, round(image.get_width() * scale)), height)
    return pygame.transform.smoothscale(image, size)


def load_split_sprites(filename, height, count=2):
    path = os.path.join(ASSET_DIR, filename)
    try:
        image = pygame.image.load(path).convert_alpha()
    except (pygame.error, FileNotFoundError):
        return []
    image = crop_to_alpha(remove_edge_black_background(image), padding=0)
    cell_w = image.get_width() // count
    sprites = []
    for index in range(count):
        cell = image.subsurface(pygame.Rect(index * cell_w, 0, cell_w, image.get_height())).copy()
        cell = crop_to_alpha(cell)
        scale = height / cell.get_height()
        size = (max(1, round(cell.get_width() * scale)), height)
        sprites.append(pygame.transform.smoothscale(cell, size))
    return sprites


def load_separated_sprites(filename, height, count=2):
    path = os.path.join(ASSET_DIR, filename)
    try:
        image = pygame.image.load(path).convert_alpha()
    except (pygame.error, FileNotFoundError):
        return []
    image = crop_to_alpha(remove_edge_black_background(image), padding=0)
    active_columns = []
    for x in range(image.get_width()):
        active_columns.append(any(image.get_at((x, y)).a > 8 for y in range(image.get_height())))

    runs = []
    start = None
    for x, active in enumerate(active_columns):
        if active and start is None:
            start = x
        elif not active and start is not None:
            runs.append((start, x - 1))
            start = None
    if start is not None:
        runs.append((start, len(active_columns) - 1))

    if len(runs) < count:
        return load_split_sprites(filename, height, count)

    sprites = []
    for start, end in runs[:count]:
        cell = image.subsurface(pygame.Rect(start, 0, end - start + 1, image.get_height())).copy()
        cell = crop_to_alpha(cell)
        scale = height / cell.get_height()
        size = (max(1, round(cell.get_width() * scale)), height)
        sprites.append(pygame.transform.smoothscale(cell, size))
    return sprites


def load_cover_image(filename, size):
    path = os.path.join(ASSET_DIR, filename)
    try:
        image = pygame.image.load(path).convert_alpha()
    except (pygame.error, FileNotFoundError):
        return None
    scale = max(size[0] / image.get_width(), size[1] / image.get_height())
    scaled_size = (max(1, round(image.get_width() * scale)), max(1, round(image.get_height() * scale)))
    image = pygame.transform.smoothscale(image, scaled_size)
    rect = image.get_rect(center=(size[0] // 2, size[1] // 2))
    return image.subsurface(pygame.Rect(-rect.x, -rect.y, size[0], size[1])).copy()


TITLE_BACKGROUND = load_cover_image("title_background.png", (WIDTH, HEIGHT))
START_BUTTON_SPRITE = load_sprite("start_button.png", 78)
BANANA_SPRITE = load_sprite("banana.png", 42)
DEVICE_SPRITES = {
    "lamp": load_sprite("lamp.png", 58),
    "fridge": load_sprite("fridge.png", 82),
    "ac": load_sprite("ac.png", 45),
    "outlet": load_sprite("outlet.png", 34),
    "fan": load_sprite("fan.png", 58),
}
DEVICE_STATE_SPRITES = {
    "light": load_split_sprites("switch.png", 42),
    "sink": load_split_sprites("sink.png", 58),
}
TOILET_SPRITE = load_sprite("toilet.png", 74)
BATHTUB_SPRITE = load_sprite("bathtub.png", 58)
BED_SPRITE = load_sprite("bed.png", 104)
SOFA_SPRITES = load_separated_sprites("sofa.png", 96)
SOFA_FRONT_SPRITE = SOFA_SPRITES[0] if len(SOFA_SPRITES) > 0 else None
SOFA_SIDE_SPRITE = SOFA_SPRITES[1] if len(SOFA_SPRITES) > 1 else None
COFFEE_TABLE_SPRITE = load_sprite("coffee_table.png", 52)


ROOM_ORDER = [
    "living", "entry", "kitchen", "study", "master", "bed1", "bed2", "bed3",
    "dress", "bath1", "bath2", "utility", "pantry", "balcony",
]

ROOM_LABELS = {
    "living": "거실",
    "entry": "현관",
    "kitchen": "주방",
    "study": "서재",
    "master": "안방",
    "bed1": "침실1",
    "bed2": "침실2",
    "bed3": "침실3",
    "dress": "드레스룸",
    "bath1": "화장실1",
    "bath2": "화장실2",
    "utility": "다용도실",
    "pantry": "팬트리",
    "balcony": "베란다",
}

TILED_ROOMS = {"entry", "bath1", "bath2", "utility", "balcony"}
SPECIAL_LIVING_ONLY = {"entry", "balcony"}
GLOBAL_HOUSE_AREAS = []
GLOBAL_COLLISION_WALLS = []
GLOBAL_FURNITURE_COLLISIONS = []
ACTIVE_DOORS = []


class Room:
    def __init__(self, room_id, grid_pos, rect):
        self.id = room_id
        self.name = ROOM_LABELS[room_id]
        self.grid = grid_pos
        self.rect = rect
        self.tile = room_id in TILED_ROOMS


class Door:
    def __init__(self, rect, vertical):
        self.opening = rect.copy()
        self.vertical = vertical
        self.closed = False
        self.close_flash = 0.0

    @property
    def center(self):
        return pygame.Vector2(self.opening.center)

    @property
    def block_rect(self):
        if self.vertical:
            return pygame.Rect(self.opening.centerx - 8, self.opening.centery - 34, 16, 68)
        return pygame.Rect(self.opening.centerx - 34, self.opening.centery - 8, 68, 16)

    def open(self):
        if not self.closed:
            return False
        self.closed = False
        return True

    def close(self, blockers=()):
        if self.closed:
            return False
        if any(self.block_rect.colliderect(blocker.collision_rect()) for blocker in blockers):
            return False
        self.closed = True
        self.close_flash = 0.8
        return True

    def draw(self, surface):
        pygame.draw.rect(surface, COLORS["corridor"], self.opening.inflate(22, 22))
        if self.closed:
            panel = self.block_rect
            draw_3d_rect(surface, panel, COLORS["wood"], COLORS["wood_dark"], height=4, radius=4)
            if self.vertical:
                knob = (panel.centerx + 5, panel.centery)
                pygame.draw.line(surface, (181, 119, 63), (panel.centerx, panel.top + 7), (panel.centerx, panel.bottom - 7), 1)
            else:
                knob = (panel.centerx, panel.centery + 5)
                pygame.draw.line(surface, (181, 119, 63), (panel.left + 7, panel.centery), (panel.right - 7, panel.centery), 1)
            pygame.draw.circle(surface, (241, 204, 103), knob, 4)
        if self.close_flash > 0:
            self.close_flash = max(0, self.close_flash - 0.05)
            pygame.draw.rect(surface, COLORS["warn"], self.block_rect.inflate(8, 8), 2, border_radius=5)


def subtract_rect(rect, cutter):
    if not rect.colliderect(cutter):
        return [rect]
    hit = rect.clip(cutter)
    pieces = []
    if rect.top < hit.top:
        pieces.append(pygame.Rect(rect.left, rect.top, rect.w, hit.top - rect.top))
    if hit.bottom < rect.bottom:
        pieces.append(pygame.Rect(rect.left, hit.bottom, rect.w, rect.bottom - hit.bottom))
    if rect.left < hit.left:
        pieces.append(pygame.Rect(rect.left, hit.top, hit.left - rect.left, hit.h))
    if hit.right < rect.right:
        pieces.append(pygame.Rect(hit.right, hit.top, rect.right - hit.right, hit.h))
    return [p for p in pieces if p.w > 0 and p.h > 0]


def room_dimensions(room_id):
    units = ROOM_SIZE_UNITS.get(room_id, 5)
    scale = 0.45 + 0.55 * (units / ROOM_SIZE_UNITS["living"])
    width = max(MIN_ROOM_W, round(ROOM_W * scale))
    height = max(MIN_ROOM_H, round(ROOM_H * scale))
    return width, height


class MapGenerator:
    def __init__(self):
        self.center = pygame.Vector2(WORLD_WIDTH // 2, WORLD_HEIGHT // 2)
        self.visual_offsets = {}

    def build(self):
        for _ in range(800):
            layout = self.try_build_layout()
            if layout:
                return layout
        raise RuntimeError("랜덤 맵 생성 실패")

    def try_build_layout(self):
        positions = {"living": (0, 0)}
        candidates = [(x, y) for x in range(-4, 5) for y in range(-4, 5) if 0 < abs(x) + abs(y) <= 4]
        adjacent = [(1, 0), (-1, 0), (0, 1), (0, -1)]
        random.shuffle(adjacent)
        positions["entry"] = adjacent[0]
        positions["balcony"] = adjacent[1]
        used = {positions["living"], positions["entry"], positions["balcony"]}

        edges = {
            tuple(sorted(("living", "entry"))),
            tuple(sorted(("living", "balcony"))),
        }
        degree = {"living": 2, "entry": 1, "balcony": 1}
        depth = {"living": 0, "entry": 1, "balcony": 1}
        connected_rooms = ["living"]

        def free_cells():
            return [cell for cell in candidates if cell not in used]

        def parent_candidates():
            return [
                room_id for room_id in connected_rooms
                if room_id not in SPECIAL_LIVING_ONLY and degree.get(room_id, 0) < 3 and depth.get(room_id, 0) < 4
            ]

        def frontier_cells_for(parent_id):
            parent_cell = positions[parent_id]
            cells = [
                cell for cell in free_cells()
                if self.is_adjacent(cell, parent_cell)
            ]
            cells.sort(key=lambda p: random.random() + abs(abs(p[0]) + abs(p[1]) - min(4, depth[parent_id] + 1)) * 0.15)
            return cells

        def add_edge(a, b):
            edges.add(tuple(sorted((a, b))))
            degree[a] = degree.get(a, 0) + 1
            degree[b] = degree.get(b, 0) + 1

        master_options = []
        for master_cell in [cell for cell in free_cells() if self.is_adjacent(cell, positions["living"])]:
            for dress_cell in free_cells():
                if dress_cell != master_cell and self.is_adjacent(master_cell, dress_cell):
                    master_options.append((master_cell, dress_cell, "living"))
        if not master_options:
            return None
        positions["master"], positions["dress"], parent = random.choice(master_options)
        used.update((positions["master"], positions["dress"]))
        depth["master"] = depth[parent] + 1
        depth["dress"] = depth["master"] + 1
        add_edge(parent, "master")
        add_edge("master", "dress")
        connected_rooms.extend(["master", "dress"])

        rest = [room for room in ROOM_ORDER if room not in positions]
        random.shuffle(rest)
        for room_id in rest:
            parents = parent_candidates()
            if not parents:
                return None
            parents.sort(key=lambda p: (
                0 if degree.get(p, 0) < 2 else 1,
                depth[p],
                random.random(),
            ))
            placed = False
            for parent in parents:
                frontier = frontier_cells_for(parent)
                if not frontier:
                    continue
                cell = frontier[0]
                positions[room_id] = cell
                used.add(cell)
                depth[room_id] = depth[parent] + 1
                degree[room_id] = 0
                connected_rooms.append(room_id)
                add_edge(parent, room_id)
                placed = True
                break
            if not placed:
                return None

        if max(depth.values()) > 4:
            return None

        if any(count > 3 for count in degree.values()):
            return None

        if sum(1 for count in degree.values() if count > 2) > 4:
            return None

        if not self.valid_edges(edges):
            return None

        self.visual_offsets = self.make_visual_offsets(positions)
        rooms = {
            room_id: Room(room_id, grid, self.rect_for_grid(room_id, grid))
            for room_id, grid in positions.items()
        }
        self.snap_connected_rooms(rooms, edges)
        corridors, doors, passages = self.build_connectors(rooms, edges)
        areas = [room.rect for room in rooms.values()] + corridors
        walls = self.build_walls(rooms.values(), passages)
        return {"rooms": rooms, "edges": edges, "corridors": corridors, "doors": doors, "areas": areas, "walls": walls}

    def build_edges(self, positions):
        edges = set()
        for room_id, grid in positions.items():
            if room_id in SPECIAL_LIVING_ONLY:
                edges.add(tuple(sorted(("living", room_id))))
                continue
            if room_id == "living":
                continue
            neighbors = [
                other_id for other_id, other_grid in positions.items()
                if other_id not in SPECIAL_LIVING_ONLY and self.is_adjacent(grid, other_grid)
            ]
            if room_id == "dress":
                edges.add(tuple(sorted(("master", "dress"))))
                continue
            close_neighbors = sorted(neighbors, key=lambda r: self.graph_bias(r, positions))
            if close_neighbors:
                edges.add(tuple(sorted((room_id, close_neighbors[0]))))

        for room_id, grid in positions.items():
            if room_id in {"living", "entry", "balcony"}:
                continue
            if self.is_adjacent(grid, positions["living"]) and random.random() < 0.7:
                edges.add(tuple(sorted(("living", room_id))))

        physical = [
            tuple(sorted((a, b))) for a, ga in positions.items() for b, gb in positions.items()
            if a < b and a not in SPECIAL_LIVING_ONLY and b not in SPECIAL_LIVING_ONLY and self.is_adjacent(ga, gb)
        ]
        random.shuffle(physical)
        for edge in physical[:8]:
            if random.random() < 0.45:
                edges.add(edge)
        return edges

    def valid_edges(self, edges):
        if tuple(sorted(("master", "dress"))) not in edges:
            return False
        degree = {room_id: 0 for room_id in ROOM_ORDER}
        graph = {room_id: [] for room_id in ROOM_ORDER}
        for a, b in edges:
            degree[a] += 1
            degree[b] += 1
            graph[a].append(b)
            graph[b].append(a)
        if any(count > 3 for count in degree.values()):
            return False
        for special in SPECIAL_LIVING_ONLY:
            if tuple(sorted(("living", special))) not in edges:
                return False
            if sum(1 for e in edges if special in e) != 1:
                return False
        distances = {"living": 0}
        queue = ["living"]
        for room_id in queue:
            for nxt in graph[room_id]:
                if nxt not in distances:
                    distances[nxt] = distances[room_id] + 1
                    queue.append(nxt)
        return set(distances) == set(ROOM_ORDER) and max(distances.values()) <= 4

    def build_connectors(self, rooms, edges):
        corridors, doors, passages = [], [], []
        for a_id, b_id in sorted(edges):
            a, b = rooms[a_id].rect, rooms[b_id].rect
            if abs(rooms[a_id].grid[0] - rooms[b_id].grid[0]) == 1:
                left, right = (a, b) if a.centerx < b.centerx else (b, a)
                y = (left.centery + right.centery) // 2
                gap = max(0, right.left - left.right)
                corridor = pygame.Rect(left.right - 26, y - DOOR_SIZE // 2, gap + 52, DOOR_SIZE)
                door_rect = pygame.Rect(corridor.centerx - 10, y - DOOR_SIZE // 2, 20, DOOR_SIZE)
                passages.extend([
                    pygame.Rect(left.right - 30, y - DOOR_SIZE // 2 - 10, 60, DOOR_SIZE + 20),
                    pygame.Rect(right.left - 30, y - DOOR_SIZE // 2 - 10, 60, DOOR_SIZE + 20),
                ])
                doors.append(Door(door_rect, True))
            else:
                top, bottom = (a, b) if a.centery < b.centery else (b, a)
                x = (top.centerx + bottom.centerx) // 2
                gap = max(0, bottom.top - top.bottom)
                corridor = pygame.Rect(x - DOOR_SIZE // 2, top.bottom - 26, DOOR_SIZE, gap + 52)
                door_rect = pygame.Rect(x - DOOR_SIZE // 2, corridor.centery - 10, DOOR_SIZE, 20)
                passages.extend([
                    pygame.Rect(x - DOOR_SIZE // 2 - 10, top.bottom - 30, DOOR_SIZE + 20, 60),
                    pygame.Rect(x - DOOR_SIZE // 2 - 10, bottom.top - 30, DOOR_SIZE + 20, 60),
                ])
                doors.append(Door(door_rect, False))
            corridors.append(corridor)
        return corridors, doors, passages

    def snap_connected_rooms(self, rooms, edges):
        for a_id, b_id in sorted(edges):
            room_a, room_b = rooms[a_id], rooms[b_id]
            a, b = room_a.rect, room_b.rect
            if abs(room_a.grid[0] - room_b.grid[0]) == 1:
                left, right = (a, b) if a.centerx < b.centerx else (b, a)
                seam = round((left.right + right.left) / 2)
                old_right = right.right
                left.w = max(80, seam - left.left)
                right.x = seam
                right.w = max(80, old_right - seam)
            else:
                top, bottom = (a, b) if a.centery < b.centery else (b, a)
                seam = round((top.bottom + bottom.top) / 2)
                old_bottom = bottom.bottom
                top.h = max(80, seam - top.top)
                bottom.y = seam
                bottom.h = max(80, old_bottom - seam)

    def make_visual_offsets(self, positions):
        offsets = {"living": (0, 0)}
        for room_id in positions:
            if room_id == "living":
                continue
            if room_id in SPECIAL_LIVING_ONLY:
                limit_x, limit_y = 18, 14
            else:
                limit_x, limit_y = 34, 26
            offsets[room_id] = (random.randint(-limit_x, limit_x), random.randint(-limit_y, limit_y))
        return offsets

    def build_walls(self, rooms, passages):
        thickness = 16
        walls = []
        cutters = [p.inflate(8, 8) for p in passages]
        for room in rooms:
            rect = room.rect
            segments = [
                pygame.Rect(rect.left, rect.top, rect.w, thickness),
                pygame.Rect(rect.left, rect.bottom - thickness, rect.w, thickness),
                pygame.Rect(rect.left, rect.top, thickness, rect.h),
                pygame.Rect(rect.right - thickness, rect.top, thickness, rect.h),
            ]
            for segment in segments:
                parts = [segment]
                for cutter in cutters:
                    next_parts = []
                    for part in parts:
                        next_parts.extend(subtract_rect(part, cutter))
                    parts = next_parts
                walls.extend(parts)
        seen, unique = set(), []
        for wall in walls:
            key = (wall.x, wall.y, wall.w, wall.h)
            if key not in seen:
                seen.add(key)
                unique.append(wall)
        return unique

    def rect_for_grid(self, room_id, grid):
        width, height = room_dimensions(room_id)
        offset = self.visual_offsets.get(room_id, (0, 0))
        center = pygame.Vector2(
            self.center.x + grid[0] * CELL_W + offset[0],
            self.center.y + grid[1] * CELL_H + offset[1],
        )
        return pygame.Rect(
            round(center.x - width / 2),
            round(center.y - height / 2),
            width,
            height,
        )

    @staticmethod
    def is_adjacent(a, b):
        return abs(a[0] - b[0]) + abs(a[1] - b[1]) == 1

    @staticmethod
    def graph_bias(room_id, positions):
        grid = positions[room_id]
        return abs(grid[0]) + abs(grid[1]) + random.random()


class Device:
    TYPES = {
        "light": {"label": "전등스위치", "watts": 60, "size": (26, 34), "on": COLORS["yellow"], "off": COLORS["off"]},
        "outlet": {"label": "콘센트", "watts": 180, "size": (30, 30), "on": COLORS["orange"], "off": COLORS["off"]},
        "ac": {"label": "에어컨", "watts": 1500, "size": (116, 45), "on": COLORS["blue"], "off": (172, 194, 204)},
        "lamp": {"label": "램프", "watts": 40, "size": (44, 58), "on": COLORS["yellow"], "off": COLORS["off"]},
        "fan": {"label": "선풍기", "watts": 50, "size": (38, 38), "on": COLORS["blue"], "off": COLORS["off"]},
        "fridge": {"label": "냉장고", "watts": 220, "size": (58, 82), "on": (116, 205, 224), "off": (177, 200, 204)},
        "sink": {"label": "세면대", "watts": 0, "size": (58, 38), "on": (96, 184, 230), "off": (205, 218, 218)},
    }

    def __init__(self, dtype, room_id, x, y, glow_rect=None, wall_side=None):
        self.dtype = dtype
        self.room_id = room_id
        self.x = float(x)
        self.y = float(y)
        self.wall_side = wall_side
        data = self.TYPES[dtype]
        self.label = data["label"]
        self.watts = data["watts"]
        self.w, self.h = data["size"]
        self.sprite = DEVICE_SPRITES.get(dtype)
        self.state_sprites = DEVICE_STATE_SPRITES.get(dtype, [])
        if self.sprite and self.dtype == "ac":
            if wall_side == "left":
                self.sprite = pygame.transform.rotate(self.sprite, 90)
            elif wall_side == "right":
                self.sprite = pygame.transform.rotate(self.sprite, -90)
            elif wall_side == "bottom":
                self.sprite = pygame.transform.rotate(self.sprite, 180)
        if self.sprite and self.dtype == "fan" and glow_rect and self.x < glow_rect.centerx:
            self.sprite = pygame.transform.flip(self.sprite, True, False)
        if self.sprite:
            self.w, self.h = self.sprite.get_size()
        elif self.state_sprites:
            self.w, self.h = self.state_sprites[0].get_size()
        self.color_on = data["on"]
        self.color_off = data["off"]
        self.on = False
        self.flash = 0.0
        self.pulse = random.uniform(0, math.tau)
        self.glow_rect = glow_rect

    @property
    def rect(self):
        return pygame.Rect(round(self.x - self.w / 2), round(self.y - self.h / 2), self.w, self.h)

    @property
    def pos(self):
        return pygame.Vector2(self.x, self.y)

    def turn_on(self):
        if not self.on:
            self.on = True
            self.flash = 0.7

    def turn_off(self):
        if not self.on:
            return 0
        self.on = False
        self.flash = 1.0
        return self.watts

    def draw(self, surface, t):
        rect = self.rect
        draw_shadow(surface, pygame.Rect(rect.x + 3, rect.y + rect.h - 2, rect.w, 14), 42)
        if self.on and self.dtype == "lamp":
            glow = pygame.Surface((rect.w + 58, rect.h + 58), pygame.SRCALPHA)
            pygame.draw.ellipse(glow, (255, 237, 110, 65), glow.get_rect())
            surface.blit(glow, (rect.x - 29, rect.y - 29))

        color = self.color_on if self.on else self.color_off
        if not self.sprite and not self.state_sprites:
            draw_3d_rect(surface, rect, color, height=7, radius=6)
        if self.dtype == "light":
            if self.state_sprites:
                surface.blit(self.state_sprites[1 if self.on else 0], rect)
            else:
                plate = rect.inflate(-6, -7)
                pygame.draw.rect(surface, (245, 245, 232), plate, border_radius=3)
                pygame.draw.rect(surface, COLORS["black"], plate, 1, border_radius=3)
                knob_y = plate.top + 8 if self.on else plate.bottom - 8
                pygame.draw.rect(surface, COLORS["green"] if self.on else (115, 120, 116), (plate.centerx - 4, knob_y - 5, 8, 10), border_radius=2)
        elif self.dtype == "outlet":
            if self.sprite:
                surface.blit(self.sprite, rect)
            else:
                pygame.draw.circle(surface, COLORS["black"], (rect.centerx - 5, rect.centery), 2)
                pygame.draw.circle(surface, COLORS["black"], (rect.centerx + 5, rect.centery), 2)
        elif self.dtype == "ac":
            if self.sprite:
                surface.blit(self.sprite, rect)
            else:
                pygame.draw.rect(surface, (238, 248, 255), rect.inflate(-12, -14), border_radius=3)
            if self.on:
                self.draw_ac_wind(surface, rect, t)
        elif self.dtype == "lamp":
            if self.sprite:
                surface.blit(self.sprite, rect)
            else:
                pygame.draw.polygon(surface, (255, 245, 145) if self.on else (190, 190, 170), [(rect.centerx, rect.top + 4), (rect.left + 6, rect.centery), (rect.right - 6, rect.centery)])
                pygame.draw.line(surface, COLORS["black"], (rect.centerx, rect.centery), (rect.centerx, rect.bottom - 5), 2)
        elif self.dtype == "fridge":
            if self.sprite:
                surface.blit(self.sprite, rect)
            else:
                pygame.draw.line(surface, COLORS["blue_dark"], (rect.left + 7, rect.centery), (rect.right - 7, rect.centery), 2)
                if self.on:
                    pygame.draw.rect(surface, (230, 250, 255), rect.inflate(10, -10), 2, border_radius=5)
        elif self.dtype == "fan":
            if self.sprite:
                surface.blit(self.sprite, rect)
                if self.on:
                    room_centerx = self.glow_rect.centerx if self.glow_rect else self.x
                    for i, dy in enumerate((-14, 0, 14)):
                        offset = (t * 34 + i * 9) % 18
                        start_x = rect.left - 10 if self.x < room_centerx else rect.right + 10
                        direction = -1 if self.x < room_centerx else 1
                        points = [
                            (round(start_x + direction * (offset + step * 10)), round(rect.centery + dy + math.sin(t * 8 + step) * 3))
                            for step in range(4)
                        ]
                        pygame.draw.lines(surface, COLORS["blue"], False, points, 2)
            else:
                pygame.draw.circle(surface, (236, 246, 247), rect.center, 13, 2)
                angle = t * 10 if self.on else self.pulse
                for i in range(3):
                    a = angle + i * math.tau / 3
                    end = (rect.centerx + math.cos(a) * 12, rect.centery + math.sin(a) * 12)
                    pygame.draw.line(surface, COLORS["blue_dark"], rect.center, end, 3)
        elif self.dtype == "sink":
            if self.state_sprites:
                surface.blit(self.state_sprites[1 if self.on else 0], rect)
            else:
                pygame.draw.ellipse(surface, (235, 246, 247), rect.inflate(-8, -10))
                if self.on:
                    pygame.draw.line(surface, COLORS["blue"], (rect.centerx, rect.top + 8), (rect.centerx, rect.bottom + 12), 3)

        if not self.state_sprites or self.dtype in {"light", "sink"}:
            pygame.draw.circle(surface, COLORS["green"] if self.on else (105, 112, 110), (rect.right - 6, rect.y + 6), 4)
        draw_text(surface, self.label, FONT_XS, COLORS["black"], (rect.centerx, rect.bottom + 13), center=True)
        if self.flash > 0:
            self.flash = max(0, self.flash - 0.05)
            pygame.draw.rect(surface, COLORS["warn"], rect.inflate(10, 10), 2, border_radius=6)

    def draw_ac_wind(self, surface, rect, t):
        color = (116, 202, 238)
        phase = t * 7 + self.pulse
        side = self.wall_side or "top"
        if side in {"top", "bottom"}:
            direction = 1 if side == "top" else -1
            start_y = rect.bottom if direction > 0 else rect.top
            for lane, offset in enumerate((-30, 0, 30)):
                points = []
                drift = (phase * 10 + lane * 9) % 18
                for step in range(5):
                    distance = 8 + step * 12 + drift
                    x = rect.centerx + offset + math.sin(phase + step * 0.8 + lane) * 5
                    y = start_y + direction * distance
                    points.append((round(x), round(y)))
                pygame.draw.lines(surface, color, False, points, 2)
        else:
            direction = 1 if side == "left" else -1
            start_x = rect.right if direction > 0 else rect.left
            for lane, offset in enumerate((-28, 0, 28)):
                points = []
                drift = (phase * 10 + lane * 9) % 18
                for step in range(5):
                    distance = 8 + step * 12 + drift
                    x = start_x + direction * distance
                    y = rect.centery + offset + math.sin(phase + step * 0.8 + lane) * 5
                    points.append((round(x), round(y)))
                pygame.draw.lines(surface, color, False, points, 2)


class Character:
    def __init__(self, x, y, speed, skin, hair, clothes, sprite_file=None, sprite_height=78):
        self.x = float(x)
        self.y = float(y)
        self.speed = speed
        self.skin = skin
        self.hair = hair
        self.clothes = clothes
        self.sprite = load_sprite(sprite_file, sprite_height) if sprite_file else None
        self.sprite_left = pygame.transform.flip(self.sprite, True, False) if self.sprite else None
        self.walk = 0.0
        self.moving = False
        self.facing = pygame.Vector2(0, 1)
        self.look_left = False

    @property
    def pos(self):
        return pygame.Vector2(self.x, self.y)

    def collision_rect(self):
        return pygame.Rect(round(self.x - 13), round(self.y - 6), 26, 20)

    def can_stand_at(self, x, y, ignore_doors=False):
        if not any(area.collidepoint(x, y) for area in GLOBAL_HOUSE_AREAS):
            return False
        rect = pygame.Rect(round(x - 13), round(y - 6), 26, 20)
        if rect.collidelist(GLOBAL_COLLISION_WALLS) != -1:
            return False
        if rect.collidelist(GLOBAL_FURNITURE_COLLISIONS) != -1:
            return False
        if ignore_doors:
            return True
        closed_doors = [door.block_rect for door in ACTIVE_DOORS if door.closed]
        return rect.collidelist(closed_doors) == -1

    def move(self, dx, dy):
        if dx == 0 and dy == 0:
            self.moving = False
            return False
        vec = pygame.Vector2(dx, dy)
        if vec.length_squared():
            vec = vec.normalize() * self.speed
            self.facing = vec.normalize()
            if abs(self.facing.x) > 0.2:
                self.look_left = self.facing.x < 0
        old_x, old_y = self.x, self.y
        next_x = self.x + vec.x
        if self.can_stand_at(next_x, self.y):
            self.x = next_x
        next_y = self.y + vec.y
        if self.can_stand_at(self.x, next_y):
            self.y = next_y
        self.moving = self.x != old_x or self.y != old_y
        if self.moving:
            self.walk += 0.13
        return self.moving

    def draw(self, surface, name):
        cx, cy = round(self.x), round(self.y)
        bob = math.sin(self.walk * 2.6) * 2 if self.moving else 0
        if self.sprite:
            sprite = self.sprite_left if self.look_left else self.sprite
            sw, _ = sprite.get_size()
            draw_shadow(surface, pygame.Rect(cx - sw // 3, cy + 7, sw * 2 // 3, 14), 55)
            surface.blit(sprite, sprite.get_rect(midbottom=(cx, cy + 12 + round(bob))))
            draw_text(surface, name, FONT_XS, COLORS["black"], (cx, cy + 31), center=True)
            return
        draw_shadow(surface, pygame.Rect(cx - 17, cy + 10, 34, 12), 55)
        pygame.draw.circle(surface, self.skin, (cx, cy - 18), 12)
        pygame.draw.ellipse(surface, self.clothes, (cx - 12, cy - 5, 24, 24))
        draw_text(surface, name, FONT_XS, COLORS["black"], (cx, cy + 32), center=True)


class Mom(Character):
    def __init__(self, x, y):
        super().__init__(x, y, 5.1, (255, 193, 132), (72, 43, 25), (93, 178, 112), "mom.png", 82)
        self.range = 66
        self.message = ""
        self.message_timer = 0
        self.stun_timer = 0.0

    def update(self, keys, dt):
        if self.stun_timer > 0:
            self.stun_timer = max(0, self.stun_timer - dt)
            self.moving = False
        else:
            dx = (keys[pygame.K_RIGHT] or keys[pygame.K_d]) - (keys[pygame.K_LEFT] or keys[pygame.K_a])
            dy = (keys[pygame.K_DOWN] or keys[pygame.K_s]) - (keys[pygame.K_UP] or keys[pygame.K_w])
            self.move(dx, dy)
        if self.message_timer > 0:
            self.message_timer -= 1

    def interact_devices(self, devices):
        nearby = [
            device for device in devices
            if device.on and self.pos.distance_to(device.pos) <= self.range
        ]
        handled = []
        saved = 0
        if nearby:
            device = min(nearby, key=lambda item: self.pos.distance_to(item.pos))
            saved = device.turn_off()
            handled.append(device)
        if handled:
            self.message = f"{handled[0].label} 처리!"
            self.message_timer = 70
        else:
            self.message = "가까운 낭비가 없어요"
            self.message_timer = 45
        return saved, handled

    def draw(self, surface, name="엄마"):
        super().draw(surface, name)
        if self.stun_timer > 0:
            draw_text(surface, "미끄러짐!", FONT_XS, COLORS["danger"], (self.x, self.y - 58), center=True)
        if self.message_timer > 0:
            msg = FONT_SM.render(self.message, True, COLORS["text"])
            box = pygame.Rect(0, 0, msg.get_width() + 16, 26)
            box.center = (self.x, self.y - 44)
            bubble = pygame.Surface(box.size, pygame.SRCALPHA)
            pygame.draw.rect(bubble, (*COLORS["ui"], 220), bubble.get_rect(), border_radius=8)
            surface.blit(bubble, box)
            surface.blit(msg, (box.x + 8, box.y + 4))


class Son(Character):
    def __init__(self, x, y):
        super().__init__(x, y, 5.8, (255, 198, 138), (62, 42, 25), (80, 150, 220), "son.png", 76)
        self.target = None
        self.path = []
        self.wait = random.uniform(0.5, 1.1)
        self.status = "놀러 다니는 중"
        self.door_timer = 0.0
        self.banana_timer = random.uniform(8, 14)

    def update(self, devices, doors, bananas, blockers, dt):
        self.door_timer = max(0, self.door_timer - dt)
        self.banana_timer -= dt
        if self.banana_timer <= 0 and len(bananas) < 6:
            bananas.append(Banana(self.x, self.y))
            self.banana_timer = random.uniform(8, 14)

        if self.target and self.target.on:
            self.target = None
            self.path = []
        if not self.target:
            self.wait -= dt
            self.move(0, 0)
            if self.wait <= 0:
                self.target = self.choose_target(devices)
                if self.target:
                    self.path = self.find_path(self.target.pos)
                    self.status = f"{self.target.label} 켜러 감"
                self.wait = random.uniform(0.4, 1.1)
            elif random.random() < 0.02:
                self.move(random.uniform(-1, 1), random.uniform(-1, 1))
                self.close_nearby_door(doors, blockers)
            return

        if self.pos.distance_to(self.target.pos) <= 30:
            self.target.turn_on()
            self.status = f"{self.target.label} 켰다!"
            self.target = None
            self.path = []
            self.wait = random.uniform(0.35, 0.9)
            return

        if not self.path:
            self.path = self.find_path(self.target.pos)
        direction = self.next_direction(self.target.pos - self.pos)
        self.open_path_door(doors)
        self.open_blocking_door(doors, direction)
        if not self.move(direction.x, direction.y):
            self.open_nearest_closed_door(doors)
            self.snap_to_nearby_waypoint()
            if not self.path:
                self.path = self.find_path(self.target.pos)
        self.close_nearby_door(doors, blockers)

    def choose_target(self, devices):
        choices = [d for d in devices if not d.on]
        if not choices:
            return None

        def pick_reachable(pool, max_checks=10):
            random.shuffle(pool)
            reachable = []
            for device in pool[:max_checks]:
                if self.find_path(device.pos):
                    reachable.append(device)
                    if len(reachable) >= 4:
                        break
            return random.choice(reachable) if reachable else None

        if random.random() < 0.45:
            special = pick_reachable([d for d in choices if d.dtype in {"fridge", "sink"}])
            if special:
                return special
        if random.random() < 0.55:
            high_waste = pick_reachable([d for d in choices if d.dtype in {"ac", "outlet", "fan"}])
            if high_waste:
                return high_waste
        return pick_reachable(choices, 14)

    def next_direction(self, fallback_delta):
        while self.path and self.pos.distance_to(self.path[0]) < 12:
            self.path.pop(0)
        if self.path:
            delta = self.path[0] - self.pos
            if delta.length_squared():
                return delta.normalize()
        return fallback_delta.normalize() if fallback_delta.length_squared() else pygame.Vector2(0, 1)

    def find_path(self, target_pos):
        step = 20
        start = self.nearest_nav_cell(self.pos, step)
        goal_cells = self.nav_goal_cells(target_pos, step)
        if start is None or not goal_cells:
            return []
        goals = set(goal_cells)

        def passable(cell):
            return self.can_stand_at(cell[0] * step, cell[1] * step, ignore_doors=True)

        frontier = [(0, start)]
        came_from = {start: None}
        cost_so_far = {start: 0}
        reached_goal = None
        while frontier and len(came_from) < 12000:
            _, current = heapq.heappop(frontier)
            if current in goals:
                reached_goal = current
                break
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (1, -1), (-1, 1), (-1, -1)):
                nxt = (current[0] + dx, current[1] + dy)
                if not passable(nxt):
                    continue
                new_cost = cost_so_far[current] + (1.4 if dx and dy else 1)
                if nxt not in cost_so_far or new_cost < cost_so_far[nxt]:
                    cost_so_far[nxt] = new_cost
                    heuristic = min(abs(goal[0] - nxt[0]) + abs(goal[1] - nxt[1]) for goal in goal_cells[:12])
                    priority = new_cost + heuristic
                    heapq.heappush(frontier, (priority, nxt))
                    came_from[nxt] = current
        if reached_goal is None:
            return []
        cells = []
        current = reached_goal
        while current != start:
            cells.append(current)
            current = came_from[current]
        cells.reverse()
        return [pygame.Vector2(cell[0] * step, cell[1] * step) for cell in cells]

    def nav_goal_cells(self, pos, step):
        base = (round(pos.x / step), round(pos.y / step))
        cells = []
        for radius in range(11):
            for dx in range(-radius, radius + 1):
                for dy in range(-radius, radius + 1):
                    if max(abs(dx), abs(dy)) == radius:
                        cell = (base[0] + dx, base[1] + dy)
                        if self.can_stand_at(cell[0] * step, cell[1] * step, ignore_doors=True):
                            cells.append(cell)
            if len(cells) >= 10:
                break
        cells.sort(key=lambda c: (c[0] * step - pos.x) ** 2 + (c[1] * step - pos.y) ** 2)
        return cells

    def nearest_nav_cell(self, pos, step):
        base = (round(pos.x / step), round(pos.y / step))
        for radius in range(8):
            cells = []
            for dx in range(-radius, radius + 1):
                for dy in range(-radius, radius + 1):
                    if max(abs(dx), abs(dy)) == radius:
                        cells.append((base[0] + dx, base[1] + dy))
            cells.sort(key=lambda c: (c[0] * step - pos.x) ** 2 + (c[1] * step - pos.y) ** 2)
            for cell in cells:
                if self.can_stand_at(cell[0] * step, cell[1] * step, ignore_doors=True):
                    return cell
        return None

    def point_collision_rect(self, point):
        return pygame.Rect(round(point.x - 13), round(point.y - 6), 26, 20)

    def snap_to_nearby_waypoint(self):
        if not self.path:
            return False
        waypoint = self.path[0]
        if self.pos.distance_to(waypoint) > 34:
            return False
        for door in ACTIVE_DOORS:
            if door.closed and self.point_collision_rect(waypoint).colliderect(door.block_rect):
                door.open()
        if not self.can_stand_at(waypoint.x, waypoint.y):
            return False
        self.x, self.y = waypoint.x, waypoint.y
        self.path.pop(0)
        return True

    def open_path_door(self, doors):
        if not self.path:
            return
        waypoint_rect = self.point_collision_rect(self.path[0])
        for door in doors:
            if door.closed and waypoint_rect.colliderect(door.block_rect.inflate(8, 8)):
                door.open()
                return

    def open_blocking_door(self, doors, direction):
        ahead = self.pos + direction * 42
        for door in doors:
            if door.closed and door.block_rect.collidepoint(ahead.x, ahead.y):
                door.open()
                return

    def open_nearest_closed_door(self, doors):
        nearby = [door for door in doors if door.closed and self.pos.distance_to(door.center) < 70]
        if nearby:
            min(nearby, key=lambda d: self.pos.distance_to(d.center)).open()

    def close_nearby_door(self, doors, blockers):
        if self.door_timer > 0:
            return
        open_doors = [door for door in doors if not door.closed and self.pos.distance_to(door.center) < 72]
        if self.path:
            waypoint_rect = self.point_collision_rect(self.path[0])
            open_doors = [door for door in open_doors if not waypoint_rect.colliderect(door.block_rect.inflate(18, 18))]
        if open_doors and min(open_doors, key=lambda d: self.pos.distance_to(d.center)).close(blockers):
            self.status = "문 닫고 감"
            self.door_timer = 0.8

    def draw(self, surface, name="아들"):
        super().draw(surface, name)
        if self.target:
            label = FONT_XS.render(self.status, True, COLORS["danger"])
            rect = label.get_rect(center=(self.x, self.y - 54)).inflate(12, 8)
            pygame.draw.rect(surface, COLORS["white"], rect, border_radius=8)
            pygame.draw.rect(surface, COLORS["danger"], rect, 1, border_radius=8)
            surface.blit(label, label.get_rect(center=rect.center))


class Banana:
    def __init__(self, x, y):
        self.x = float(x)
        self.y = float(y)

    @property
    def pos(self):
        return pygame.Vector2(self.x, self.y)

    def draw(self, surface):
        cx, cy = round(self.x), round(self.y)
        if BANANA_SPRITE:
            draw_shadow(surface, pygame.Rect(cx - 17, cy + 8, 34, 9), 42)
            surface.blit(BANANA_SPRITE, BANANA_SPRITE.get_rect(center=(cx, cy)))
            return
        pygame.draw.arc(surface, COLORS["banana"], (cx - 12, cy - 8, 24, 18), math.pi * 0.1, math.pi * 1.1, 5)
        pygame.draw.circle(surface, (105, 78, 35), (cx + 8, cy - 2), 2)


class Particle:
    def __init__(self, x, y, color):
        self.x = x + random.uniform(-8, 8)
        self.y = y + random.uniform(-8, 8)
        self.vx = random.uniform(-2.0, 2.0)
        self.vy = random.uniform(-3.5, -1.0)
        self.life = 1.0
        self.color = color
        self.size = random.uniform(3, 7)

    def update(self, dt):
        self.x += self.vx * 60 * dt
        self.y += self.vy * 60 * dt
        self.vy += 7 * dt
        self.life -= 1.7 * dt

    def draw(self, surface):
        if self.life > 0:
            pygame.draw.circle(surface, self.color, (round(self.x), round(self.y)), max(1, round(self.size * self.life)))


class Game:
    def __init__(self):
        self.world = pygame.Surface((WORLD_WIDTH, WORLD_HEIGHT))
        self.generator = MapGenerator()
        self.show_title = True
        self.start_button = START_BUTTON_SPRITE.get_rect() if START_BUTTON_SPRITE else pygame.Rect(0, 0, 240, 64)
        self.start_button.center = (WIDTH // 2, HEIGHT - 178)
        self.title_mom = Mom(WIDTH // 2 + 235, HEIGHT // 2 + 115)
        self.reset()

    def start_game(self):
        self.reset()
        self.show_title = False

    def reset(self):
        global GLOBAL_HOUSE_AREAS, GLOBAL_COLLISION_WALLS, GLOBAL_FURNITURE_COLLISIONS, ACTIVE_DOORS
        layout = self.generator.build()
        self.rooms = layout["rooms"]
        self.edges = layout["edges"]
        self.corridors = layout["corridors"]
        self.doors = layout["doors"]
        GLOBAL_HOUSE_AREAS = layout["areas"]
        GLOBAL_COLLISION_WALLS = layout["walls"]
        ACTIVE_DOORS = self.doors

        self.devices = []
        self.create_room_devices()
        self.furniture_collision_rects = self.build_furniture_collision_rects()
        GLOBAL_FURNITURE_COLLISIONS = self.furniture_collision_rects
        living = self.rooms["living"].rect
        bed = self.rooms[random.choice(["bed1", "bed2", "bed3"])].rect
        mom_x, mom_y = self.find_free_point(living, living.center)
        son_x, son_y = self.find_free_point(bed, bed.center)
        self.mom = Mom(mom_x, mom_y)
        self.son = Son(son_x, son_y)
        self.bananas = []
        self.particles = []
        self.saved_count = 0
        self.saved_watts = 0
        self.lights_off_count = 0
        self.water_saved_count = 0
        self.risk = 12.0
        self.time_left = 60.0
        self.finished = False
        self.t = 0.0
        self.camera = pygame.Vector2(0, 0)
        self.tip_index = 0
        self.tip_timer = 0.0
        self.tips = [
            "불필요한 전등을 끄면 전기 낭비와 탄소 배출을 줄일 수 있어요.",
            "냉장고 문은 오래 열어두지 않는 습관이 중요해요.",
            "세면대 물을 잠그는 것도 지속가능한 생활입니다.",
            "바나나는 E키로 주울 수 있어요.",
        ]

        for device in random.sample(self.devices, min(8, len(self.devices))):
            device.on = True

    def create_room_devices(self):
        def add(dtype, room_id, x, y, wall_side=None):
            self.devices.append(Device(dtype, room_id, x, y, self.rooms[room_id].rect, wall_side))

        def outlet_points(rect, count):
            inset = 18
            candidates = [
                (rect.left + inset, rect.top + rect.h * 0.28),
                (rect.left + inset, rect.top + rect.h * 0.72),
                (rect.right - inset, rect.top + rect.h * 0.28),
                (rect.right - inset, rect.top + rect.h * 0.72),
                (rect.left + rect.w * 0.28, rect.top + inset),
                (rect.left + rect.w * 0.72, rect.top + inset),
                (rect.left + rect.w * 0.28, rect.bottom - inset),
                (rect.left + rect.w * 0.72, rect.bottom - inset),
            ]
            candidates = [(round(x), round(y)) for x, y in candidates]
            near_doors = [
                door for door in self.doors
                if rect.colliderect(door.opening.inflate(34, 34))
            ]

            def door_distance(point):
                if not near_doors:
                    return 9999
                pos = pygame.Vector2(point)
                return min(pos.distance_to(door.center) for door in near_doors)

            safe = [point for point in candidates if door_distance(point) > 88]
            ordered = sorted(safe if len(safe) >= count else candidates, key=door_distance, reverse=True)
            return ordered[:count]

        def room_doors(rect):
            return [door for door in self.doors if rect.colliderect(door.opening.inflate(34, 34))]

        def clamp(value, low, high):
            return max(low, min(high, value))

        def switch_point(rect):
            doors = room_doors(rect)
            if not doors:
                return rect.left + 24, rect.top + 42
            door = min(doors, key=lambda item: pygame.Vector2(rect.center).distance_to(item.center))
            offset = 54
            if door.vertical:
                x = rect.left + 18 if door.center.x < rect.centerx else rect.right - 18
                y = clamp(door.center.y + (offset if door.center.y < rect.centery else -offset), rect.top + 42, rect.bottom - 42)
            else:
                x = clamp(door.center.x + (offset if door.center.x < rect.centerx else -offset), rect.left + 42, rect.right - 42)
                y = rect.top + 18 if door.center.y < rect.centery else rect.bottom - 18
            return round(x), round(y)

        def wall_device_point(rect, dtype, preferred_sides=("left", "right", "top", "bottom")):
            def device_size_for_side(side):
                sprite = DEVICE_SPRITES.get(dtype)
                if sprite:
                    width, height = sprite.get_size()
                else:
                    width, height = Device.TYPES[dtype]["size"]
                if dtype == "ac" and side in {"left", "right"}:
                    width, height = height, width
                return width, height

            left_w, left_h = device_size_for_side("left")
            right_w, right_h = device_size_for_side("right")
            top_w, top_h = device_size_for_side("top")
            bottom_w, bottom_h = device_size_for_side("bottom")
            samples = {
                "left": [(rect.left + left_w // 2 + 12, rect.top + rect.h * ratio) for ratio in (0.28, 0.50, 0.72)],
                "right": [(rect.right - right_w // 2 - 12, rect.top + rect.h * ratio) for ratio in (0.28, 0.50, 0.72)],
                "top": [(rect.left + rect.w * ratio, rect.top + top_h // 2 + 12) for ratio in (0.28, 0.50, 0.72)],
                "bottom": [(rect.left + rect.w * ratio, rect.bottom - bottom_h // 2 - 12) for ratio in (0.28, 0.50, 0.72)],
            }
            candidates = []
            for side in preferred_sides:
                candidates.extend((round(x), round(y), side) for x, y in samples[side])
            doors = room_doors(rect)

            def score(candidate):
                pos = pygame.Vector2(candidate[0], candidate[1])
                dist = min((pos.distance_to(door.center) for door in doors), default=9999)
                side_bonus = 80 if candidate[2] in preferred_sides[:2] else 0
                return dist + side_bonus

            return sorted(candidates, key=score, reverse=True)[0]

        def corner_point(rect, dtype, index=0):
            sprite = DEVICE_SPRITES.get(dtype)
            if sprite:
                width, height = sprite.get_size()
            else:
                width, height = Device.TYPES[dtype]["size"]
            mx, my = width // 2 + 20, height // 2 + 20
            candidates = [
                (rect.left + mx, rect.top + my),
                (rect.right - mx, rect.top + my),
                (rect.left + mx, rect.bottom - my),
                (rect.right - mx, rect.bottom - my),
            ]
            doors = room_doors(rect)

            def distance_from_doors(point):
                pos = pygame.Vector2(point)
                return min((pos.distance_to(door.center) for door in doors), default=9999)

            ordered = sorted(candidates, key=distance_from_doors, reverse=True)
            return tuple(round(v) for v in ordered[index % len(ordered)])

        for room_id, room in self.rooms.items():
            r = room.rect
            if room_id == "living":
                outlets = outlet_points(r, 3)
                add("light", room_id, *switch_point(r))
                for p in outlets:
                    add("outlet", room_id, *p)
                add("ac", room_id, *wall_device_point(r, "ac", ("right", "top", "left", "bottom")))
            elif room_id == "entry":
                add("light", room_id, *switch_point(r))
            elif room_id == "kitchen":
                outlets = outlet_points(r, 2)
                add("fridge", room_id, *wall_device_point(r, "fridge", ("right", "left", "top", "bottom")))
                add("light", room_id, *switch_point(r))
                add("outlet", room_id, *outlets[0])
                add("outlet", room_id, *outlets[1])
            elif room_id == "study":
                outlets = outlet_points(r, 2)
                add("light", room_id, *switch_point(r))
                add("lamp", room_id, *corner_point(r, "lamp", 0))
                add("outlet", room_id, *outlets[0])
                add("outlet", room_id, *outlets[1])
                add("fan", room_id, *corner_point(r, "fan", 1))
            elif room_id == "master":
                outlets = outlet_points(r, 2)
                add("light", room_id, *switch_point(r))
                add("ac", room_id, *wall_device_point(r, "ac", ("right", "top", "left", "bottom")))
                add("outlet", room_id, *outlets[0])
                add("outlet", room_id, *outlets[1])
                add("lamp", room_id, *corner_point(r, "lamp", 0))
            elif room_id in {"bed1", "bed2", "bed3"}:
                outlets = outlet_points(r, 2)
                add("light", room_id, *switch_point(r))
                add("lamp", room_id, *corner_point(r, "lamp", 0))
                add("outlet", room_id, *outlets[0])
                add("outlet", room_id, *outlets[1])
                add("fan", room_id, *corner_point(r, "fan", 1))
            elif room_id == "dress":
                add("light", room_id, *switch_point(r))
            elif room_id in {"bath1", "bath2"}:
                add("sink", room_id, *wall_device_point(r, "sink", ("left", "top", "bottom")))
                add("light", room_id, *switch_point(r))
            elif room_id in {"utility", "pantry"}:
                add("light", room_id, *switch_point(r))

    def watts_on(self):
        return sum(device.watts for device in self.devices if device.on)

    def update_camera(self):
        self.camera.x = max(0, min(WORLD_WIDTH - WIDTH, self.mom.x - VIEW_CENTER.x))
        self.camera.y = max(0, min(WORLD_HEIGHT - HEIGHT, self.mom.y - VIEW_CENTER.y))

    def pick_banana_or_open_door(self):
        near_bananas = [b for b in self.bananas if self.mom.pos.distance_to(b.pos) <= self.mom.range]
        if near_bananas:
            banana = min(near_bananas, key=lambda b: self.mom.pos.distance_to(b.pos))
            self.bananas.remove(banana)
            self.mom.message = "바나나 주움!"
            self.mom.message_timer = 55
            return
        closed_doors = [d for d in self.doors if d.closed and self.mom.pos.distance_to(d.center) <= self.mom.range + 35]
        if closed_doors and min(closed_doors, key=lambda d: self.mom.pos.distance_to(d.center)).open():
            self.mom.message = "문 열림!"
            self.mom.message_timer = 55
            return
        self.mom.message = "주울 바나나/문이 없어요"
        self.mom.message_timer = 45

    def turn_off_nearby_device(self):
        saved, handled = self.mom.interact_devices(self.devices)
        if not handled:
            return
        self.saved_count += len(handled)
        self.saved_watts += saved
        self.lights_off_count += sum(1 for d in handled if d.dtype == "light")
        self.water_saved_count += sum(1 for d in handled if d.dtype == "sink")
        self.risk = max(0, self.risk - 5 - saved / 280 - self.water_saved_count)
        for _ in range(12):
            self.particles.append(Particle(self.mom.x, self.mom.y, COLORS["green"]))

    def update(self, dt):
        if self.show_title:
            self.t += dt
            return
        if self.finished:
            self.update_camera()
            return
        self.t += dt
        self.time_left -= dt
        keys = pygame.key.get_pressed()
        self.mom.update(keys, dt)
        self.son.update(self.devices, self.doors, self.bananas, (self.mom, self.son), dt)
        self.update_camera()

        for banana in list(self.bananas):
            if self.mom.stun_timer <= 0 and self.mom.pos.distance_to(banana.pos) < 24:
                self.bananas.remove(banana)
                self.mom.stun_timer = 2.0
                self.mom.message = "바나나를 밟았어요!"
                self.mom.message_timer = 70

        self.risk += (self.watts_on() / 1800 + sum(1 for d in self.devices if d.on and d.dtype == "sink") * 0.4) * dt
        self.risk = max(0, min(100, self.risk))
        for particle in self.particles:
            particle.update(dt)
        self.particles = [p for p in self.particles if p.life > 0]
        self.tip_timer += dt
        if self.tip_timer > 5:
            self.tip_timer = 0
            self.tip_index = (self.tip_index + 1) % len(self.tips)
        if self.time_left <= 0.01:
            self.time_left = 0
            self.finished = True

    def draw_floor_tiles(self, rect, tiled):
        tile = 38
        base = COLORS["floor_tile"] if tiled else COLORS["floor_wood"]
        alt = COLORS["floor_tile_2"] if tiled else COLORS["floor_wood_2"]
        for y in range(rect.y, rect.bottom, tile):
            for x in range(rect.x, rect.right, tile):
                color = alt if ((x // tile + y // tile) % 2) else base
                pygame.draw.rect(self.world, color, (x, y, min(tile, rect.right - x), min(tile, rect.bottom - y)))

    def draw_house(self):
        bounds = pygame.Rect(260, 120, WORLD_WIDTH - 520, WORLD_HEIGHT - 240)
        shadow = pygame.Surface(bounds.size, pygame.SRCALPHA)
        pygame.draw.rect(shadow, (0, 0, 0, 32), shadow.get_rect(), border_radius=24)
        self.world.blit(shadow, (bounds.x + 10, bounds.y + 18))

        for corridor in self.corridors:
            self.draw_floor_tiles(corridor, False)
        for room in self.rooms.values():
            self.draw_floor_tiles(room.rect, room.tile)

        for room_id, room in self.rooms.items():
            room_devices = [device for device in self.devices if device.room_id == room_id]
            switches = [device for device in room_devices if device.dtype == "light"]
            lamps = [device for device in room_devices if device.dtype == "lamp"]
            if switches:
                overlay = pygame.Surface(room.rect.size, pygame.SRCALPHA)
                if any(device.on for device in switches):
                    overlay.fill((255, 238, 125, 82))
                else:
                    overlay.fill((0, 0, 0, 34))
                self.world.blit(overlay, room.rect.topleft)
            if any(device.on for device in lamps):
                lamp_glow = pygame.Surface(room.rect.size, pygame.SRCALPHA)
                lamp_glow.fill((255, 226, 105, 34))
                self.world.blit(lamp_glow, room.rect.topleft)

        for wall in GLOBAL_COLLISION_WALLS:
            pygame.draw.rect(self.world, COLORS["wall"], wall)
        for door in self.doors:
            door.draw(self.world)
        self.draw_furniture()
        for room in self.rooms.values():
            draw_text(self.world, room.name, FONT_XS, COLORS["black"], room.rect.center, center=True)

    def room_furniture_items(self, room_id, room):
        r = room.rect
        items = []
        sprite_items = []
        inner = r.inflate(-28, -28)

        def item(cx, cy, fw, fh, label, min_w=34, min_h=28):
            furniture_scale = 0.76
            width = min(inner.w, max(round(min_w * 0.82), round(r.w * fw * furniture_scale)))
            height = min(inner.h, max(round(min_h * 0.82), round(r.h * fh * furniture_scale)))
            x = round(r.left + r.w * cx - width / 2)
            y = round(r.top + r.h * cy - height / 2)
            x = max(inner.left, min(inner.right - width, x))
            y = max(inner.top, min(inner.bottom - height, y))
            return pygame.Rect(x, y, width, height), label

        if room_id == "living":
            if SOFA_FRONT_SPRITE:
                use_side_sofa = SOFA_SIDE_SPRITE and r.h > r.w * 1.08
                sofa_sprite = SOFA_SIDE_SPRITE if use_side_sofa else SOFA_FRONT_SPRITE
                sofa_rect = sofa_sprite.get_rect()
                sofa_rect.center = (
                    round(r.left + r.w * (0.34 if not use_side_sofa else 0.30)),
                    round(r.top + r.h * (0.54 if not use_side_sofa else 0.48)),
                )
                sofa_rect.x = max(inner.left, min(inner.right - sofa_rect.w, sofa_rect.x))
                sofa_rect.y = max(inner.top, min(inner.bottom - sofa_rect.h, sofa_rect.y))
                sprite_items.append((sofa_rect, sofa_sprite, "소파"))
                if COFFEE_TABLE_SPRITE:
                    table_rect = COFFEE_TABLE_SPRITE.get_rect()
                    if use_side_sofa:
                        table_rect.center = (round(sofa_rect.right + table_rect.w * 0.78), sofa_rect.centery)
                    else:
                        table_rect.center = (sofa_rect.centerx, round(sofa_rect.bottom + table_rect.h * 0.62))
                    table_rect.x = max(inner.left, min(inner.right - table_rect.w, table_rect.x))
                    table_rect.y = max(inner.top, min(inner.bottom - table_rect.h, table_rect.y))
                    sprite_items.append((table_rect, COFFEE_TABLE_SPRITE, "탁자"))
                else:
                    items = [item(0.54, 0.56, 0.24, 0.22, "탁자", 58, 38)]
            else:
                items = [item(0.28, 0.52, 0.24, 0.48, "소파", 62, 70), item(0.52, 0.54, 0.24, 0.22, "탁자", 58, 38)]
        elif room_id in {"bed1", "bed2", "bed3", "master"}:
            if BED_SPRITE:
                bed_rect = BED_SPRITE.get_rect()
                bed_rect.center = (round(r.left + r.w * 0.36), round(r.top + r.h * 0.54))
                bed_rect.x = max(inner.left, min(inner.right - bed_rect.w, bed_rect.x))
                bed_rect.y = max(inner.top, min(inner.bottom - bed_rect.h, bed_rect.y))
                sprite_items.append((bed_rect, BED_SPRITE, "침대"))
                items = [item(0.78, 0.50, 0.18, 0.58, "옷장", 34, 70)]
            else:
                items = [item(0.36, 0.50, 0.48, 0.42, "침대", 82, 58), item(0.78, 0.50, 0.18, 0.58, "옷장", 34, 70)]
        elif room_id == "kitchen":
            items = [item(0.28, 0.56, 0.24, 0.60, "조리대", 42, 80), item(0.72, 0.38, 0.24, 0.34, "싱크대", 42, 42)]
        elif room_id == "study":
            items = [item(0.36, 0.58, 0.38, 0.48, "책상", 62, 58), item(0.74, 0.60, 0.20, 0.34, "의자", 32, 38)]
        elif room_id in {"bath1", "bath2"}:
            room_devices = [device for device in self.devices if device.room_id == room_id]
            avoid_points = [device.pos for device in room_devices if device.dtype == "light"]
            avoid_rects = [device.rect.inflate(34, 34) for device in room_devices if device.dtype in {"light", "sink"}]
            bath_inner = r.inflate(-16, -16)

            def bathroom_rect(sprite, fallback_rect, label, candidates):
                rects = []
                base_rect = sprite.get_rect() if sprite else fallback_rect
                for side, ratio in candidates:
                    candidate = base_rect.copy()
                    if side == "top":
                        candidate.center = (round(r.left + r.w * ratio), r.top + candidate.h // 2 + 10)
                    elif side == "bottom":
                        candidate.center = (round(r.left + r.w * ratio), r.bottom - candidate.h // 2 - 10)
                    elif side == "left":
                        candidate.center = (r.left + candidate.w // 2 + 10, round(r.top + r.h * ratio))
                    else:
                        candidate.center = (r.right - candidate.w // 2 - 10, round(r.top + r.h * ratio))
                    candidate.x = max(bath_inner.left, min(bath_inner.right - candidate.w, candidate.x))
                    candidate.y = max(bath_inner.top, min(bath_inner.bottom - candidate.h, candidate.y))
                    rects.append(candidate)

                def score(candidate):
                    center = pygame.Vector2(candidate.center)
                    point_score = min((center.distance_to(point) for point in avoid_points), default=180)
                    overlap_penalty = sum(220 for avoid in avoid_rects if candidate.colliderect(avoid))
                    return point_score - overlap_penalty

                return max(rects, key=score), label

            if BATHTUB_SPRITE:
                tub_rect, _ = bathroom_rect(
                    BATHTUB_SPRITE,
                    pygame.Rect(0, 0, max(58, r.w // 2), 42),
                    "욕조",
                    (("bottom", 0.34), ("bottom", 0.66), ("top", 0.34), ("top", 0.66)),
                )
                sprite_items.append((tub_rect, BATHTUB_SPRITE, "욕조"))
                avoid_rects.append(tub_rect.inflate(28, 28))
            else:
                items = [item(0.36, 0.60, 0.48, 0.38, "욕조", 58, 42)]
            if TOILET_SPRITE:
                toilet_rect, _ = bathroom_rect(
                    TOILET_SPRITE,
                    pygame.Rect(0, 0, 34, 42),
                    "변기",
                    (("right", 0.32), ("right", 0.68), ("left", 0.32), ("left", 0.68)),
                )
                sprite_items.append((toilet_rect, TOILET_SPRITE, "변기"))
            else:
                items.append(item(0.76, 0.58, 0.24, 0.28, "변기", 34, 32))
        elif room_id == "utility":
            items = [item(0.35, 0.57, 0.28, 0.42, "세탁기", 40, 44), item(0.67, 0.57, 0.28, 0.42, "건조기", 40, 44)]
        elif room_id == "dress":
            items = [item(0.35, 0.55, 0.28, 0.62, "옷장", 34, 56), item(0.67, 0.55, 0.28, 0.62, "옷장", 34, 56)]
        elif room_id == "pantry":
            items = [item(0.50, 0.56, 0.48, 0.55, "선반", 48, 54)]
        return items, sprite_items

    def furniture_solid_rect(self, rect, label):
        shrink = {
            "소파": (30, 26),
            "침대": (24, 22),
            "탁자": (32, 20),
            "옷장": (10, 12),
            "조리대": (10, 14),
            "싱크대": (10, 12),
            "책상": (12, 14),
            "의자": (8, 8),
            "욕조": (24, 20),
            "변기": (18, 24),
            "세면대": (18, 12),
        }.get(label, (12, 12))
        if rect.w <= shrink[0] * 2 + 8 or rect.h <= shrink[1] * 2 + 8:
            return rect.copy()
        return rect.inflate(-shrink[0] * 2, -shrink[1] * 2)

    def build_furniture_collision_rects(self):
        colliding_labels = {"소파", "침대", "탁자", "옷장", "조리대", "싱크대", "책상", "의자", "선반", "세탁기", "건조기", "욕조", "변기"}
        collisions = []
        for room_id, room in self.rooms.items():
            items, sprite_items = self.room_furniture_items(room_id, room)
            for rect, label in items:
                if label in colliding_labels:
                    collisions.append(self.furniture_solid_rect(rect, label))
            for rect, _, label in sprite_items:
                solid_label = label or "소파"
                if solid_label in colliding_labels:
                    collisions.append(self.furniture_solid_rect(rect, solid_label))
        for device in self.devices:
            if device.dtype == "sink":
                collisions.append(self.furniture_solid_rect(device.rect, "세면대"))
        return collisions

    def find_free_point(self, room_rect, preferred):
        px, py = preferred
        candidates = [(px, py)]
        for radius in range(28, max(room_rect.w, room_rect.h), 28):
            for dx, dy in ((radius, 0), (-radius, 0), (0, radius), (0, -radius), (radius, radius), (-radius, radius), (radius, -radius), (-radius, -radius)):
                candidates.append((px + dx, py + dy))
        inner = room_rect.inflate(-52, -52)
        for x, y in candidates:
            if not inner.collidepoint(x, y):
                continue
            rect = pygame.Rect(round(x - 13), round(y - 6), 26, 20)
            if rect.collidelist(GLOBAL_COLLISION_WALLS) != -1:
                continue
            if rect.collidelist(GLOBAL_FURNITURE_COLLISIONS) != -1:
                continue
            return round(x), round(y)
        return room_rect.center

    def draw_furniture(self):
        for room_id, room in self.rooms.items():
            items, sprite_items = self.room_furniture_items(room_id, room)
            for rect, label in items:
                draw_shadow(self.world, pygame.Rect(rect.x + 5, rect.y + rect.h - 2, rect.w, 15), 34)
                draw_3d_rect(self.world, rect, COLORS["wood"] if label not in {"소파", "침대", "욕조"} else (210, 200, 183))
                draw_text(self.world, label, FONT_XS, COLORS["black"], rect.center, center=True)
            for rect, sprite, label in sprite_items:
                draw_shadow(self.world, pygame.Rect(rect.x + 5, rect.y + rect.h - 2, rect.w, 15), 34)
                self.world.blit(sprite, rect)
                if label:
                    draw_text(self.world, label, FONT_XS, COLORS["black"], (rect.centerx, rect.bottom + 12), center=True)

    def draw_world(self):
        self.world.fill(COLORS["outside"])
        self.draw_house()
        for banana in self.bananas:
            banana.draw(self.world)
        drawables = self.devices + [self.son, self.mom]
        drawables.sort(key=lambda item: item.y if hasattr(item, "y") else item.rect.centery)
        for item in drawables:
            if isinstance(item, Device):
                item.draw(self.world, self.t)
            else:
                item.draw(self.world)
        for particle in self.particles:
            particle.draw(self.world)
        view = pygame.Rect(round(self.camera.x), round(self.camera.y), WIDTH, HEIGHT)
        screen.blit(self.world, (0, 0), view)

    def draw_ui(self):
        pygame.draw.rect(screen, COLORS["ui"], (0, 0, WIDTH, TOP_UI))
        pygame.draw.rect(screen, COLORS["ui_2"], (0, HEIGHT - BOTTOM_UI, WIDTH, BOTTOM_UI))
        draw_text(screen, "엄마의 에너지 절약 작전", FONT_LG, COLORS["text"], (18, 12))
        draw_text(screen, "이동: WASD/방향키   바나나/문: E   낭비 처리: SPACE   R: 다시 시작", FONT_SM, COLORS["muted"], (18, 47))
        secs = max(0, int(self.time_left))
        draw_text(screen, f"{secs:02d}", FONT_LG, COLORS["warn"] if secs < 15 else COLORS["text"], (930, 12))
        draw_text(screen, f"전등스위치 {self.lights_off_count}개   처리 {self.saved_count}개   절약 {self.saved_watts}W", FONT_SM, COLORS["green"], (18, 69))
        draw_text(screen, self.tips[self.tip_index], FONT_SM, COLORS["text"], (WIDTH // 2, HEIGHT - BOTTOM_UI // 2), center=True)
        self.draw_minimap()

    def draw_minimap(self):
        mini = pygame.Rect(WIDTH - 164, HEIGHT - 154, 144, 118)
        pygame.draw.rect(screen, (245, 247, 240), mini, border_radius=6)
        pygame.draw.rect(screen, COLORS["ui"], mini, 2, border_radius=6)
        sx, sy = mini.w / WORLD_WIDTH, mini.h / WORLD_HEIGHT
        for area in GLOBAL_HOUSE_AREAS:
            rect = pygame.Rect(mini.x + area.x * sx, mini.y + area.y * sy, max(1, area.w * sx), max(1, area.h * sy))
            pygame.draw.rect(screen, (204, 194, 166), rect)
        pygame.draw.circle(screen, COLORS["green"], (round(mini.x + self.mom.x * sx), round(mini.y + self.mom.y * sy)), 3)
        pygame.draw.circle(screen, COLORS["danger"], (round(mini.x + self.son.x * sx), round(mini.y + self.son.y * sy)), 3)

    def tree_score(self):
        return self.lights_off_count * 3 + self.saved_watts / 120 + self.water_saved_count * 2 + max(0, 100 - self.risk) / 10

    def draw_game_over(self):
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 155))
        screen.blit(overlay, (0, 0))
        panel = pygame.Rect(0, 0, 620, 360)
        panel.center = (WIDTH // 2, HEIGHT // 2)
        draw_3d_rect(screen, panel, (44, 64, 56), (25, 38, 34), height=12, radius=14)
        trees = self.tree_score() / 10
        draw_text(screen, "60초 절약 결과", FONT_LG, COLORS["green"], (panel.centerx, panel.y + 45), center=True)
        lines = [
            f"끈 전등: {self.lights_off_count}개",
            f"처리한 낭비: {self.saved_count}개",
            f"절약 전력: {self.saved_watts}W",
            f"잠근 세면대: {self.water_saved_count}개",
            f"나무 약 {trees:.1f}그루를 지킨 효과!",
            "R: 다시 도전    Q: 종료",
        ]
        for i, line in enumerate(lines):
            color = COLORS["warn"] if i == len(lines) - 1 else COLORS["text"]
            draw_text(screen, line, FONT_MD, color, (panel.centerx, panel.y + 100 + i * 38), center=True)

    def draw_title(self):
        if TITLE_BACKGROUND:
            screen.blit(TITLE_BACKGROUND, (0, 0))
        else:
            screen.fill((220, 229, 215))

        mouse_pos = pygame.mouse.get_pos()
        hover = self.start_button.collidepoint(mouse_pos)
        pressed = hover and pygame.mouse.get_pressed(num_buttons=3)[0]
        if START_BUTTON_SPRITE:
            button = START_BUTTON_SPRITE.copy()
            if pressed:
                button.fill((178, 205, 150, 255), special_flags=pygame.BLEND_RGBA_MULT)
                scale = 0.98
                y_offset = 6
            elif hover:
                button.fill((235, 255, 214, 255), special_flags=pygame.BLEND_RGBA_MULT)
                scale = 1.08
                y_offset = -3
            else:
                scale = 1.0
                y_offset = 0
            draw_w = round(button.get_width() * scale)
            draw_h = round(button.get_height() * scale)
            button = pygame.transform.smoothscale(button, (draw_w, draw_h))
            draw_rect = button.get_rect(center=(self.start_button.centerx, self.start_button.centery + y_offset))
            if hover and not pressed:
                draw_shadow(screen, pygame.Rect(draw_rect.x + 12, draw_rect.y + draw_rect.h - 6, draw_rect.w - 24, 18), 60)
            screen.blit(button, draw_rect)
        else:
            button_color = COLORS["green"] if hover else COLORS["ui_2"]
            button_dark = COLORS["green_dark"] if hover else COLORS["ui"]
            button_rect = self.start_button.move(0, 5 if pressed else 0)
            draw_3d_rect(screen, button_rect, button_color, button_dark, height=4 if pressed else 8, radius=10)
            draw_text(screen, "시작하기", FONT_LG, COLORS["white"], button_rect.center, center=True)
        draw_text(screen, "Enter 또는 Space로도 시작할 수 있어요", FONT_SM, COLORS["ui"], (self.start_button.centerx, self.start_button.bottom + 32), center=True)

    def draw(self):
        if self.show_title:
            self.draw_title()
            return
        self.draw_world()
        self.draw_ui()
        if self.finished:
            self.draw_game_over()

    def run(self):
        while True:
            dt = clock.tick(FPS) / 1000
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        pygame.quit()
                        sys.exit()
                    if self.show_title:
                        if event.key in (pygame.K_RETURN, pygame.K_SPACE):
                            self.start_game()
                        continue
                    if self.finished:
                        if event.key == pygame.K_r:
                            self.reset()
                        elif event.key == pygame.K_q:
                            pygame.quit()
                            sys.exit()
                    elif event.key == pygame.K_e:
                        self.pick_banana_or_open_door()
                    elif event.key == pygame.K_SPACE:
                        self.turn_off_nearby_device()
                    elif event.key == pygame.K_r:
                        self.reset()
                if event.type == pygame.MOUSEBUTTONDOWN and self.show_title:
                    if event.button == 1 and self.start_button.collidepoint(event.pos):
                        self.start_game()
            self.update(dt)
            self.draw()
            pygame.display.flip()


async def main():
    game = Game()

    while True:
        dt = clock.tick(FPS) / 1000

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return
                if game.show_title:
                    if event.key in (pygame.K_RETURN, pygame.K_SPACE):
                        game.start_game()
                    continue
                if game.finished:
                    if event.key == pygame.K_r:
                        game.reset()
                elif event.key == pygame.K_e:
                    game.pick_banana_or_open_door()
                elif event.key == pygame.K_SPACE:
                    game.turn_off_nearby_device()
                elif event.key == pygame.K_r:
                    game.reset()

            if event.type == pygame.MOUSEBUTTONDOWN and game.show_title:
                if event.button == 1 and game.start_button.collidepoint(event.pos):
                    game.start_game()

        

        game.update(dt)
        game.draw()
        pygame.display.flip()

        await asyncio.sleep(0)

asyncio.run(main())
