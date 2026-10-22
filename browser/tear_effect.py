# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Atul Singh Chandel

"""Viewport-only fragment animation for disposable browser tabs."""

import math
import random
import subprocess
from dataclasses import dataclass
from functools import cache

from PyQt6.QtCore import QPointF, QRect, QVariantAnimation, Qt
from PyQt6.QtGui import QColor, QPainter, QPainterPath, QPixmap
from PyQt6.QtWidgets import QWidget


@cache
def system_prefers_reduced_motion() -> bool:
    try:
        result = subprocess.run(
            ["gsettings", "get", "org.gnome.desktop.interface", "enable-animations"],
            check=True,
            capture_output=True,
            text=True,
            timeout=0.5,
        )
    except (OSError, subprocess.SubprocessError):
        return False
    return result.stdout.strip().lower() == "false"


@dataclass
class _Fragment:
    path: QPainterPath
    center: QPointF
    dx: float
    dy: float
    rotation: float
    scale: float
    delay: float


class TearEffect(QWidget):
    """Break a captured page viewport into bounded, moving image fragments."""

    def __init__(
        self,
        parent: QWidget,
        snapshot: QPixmap,
        geometry: QRect,
        background: str,
        reduced_motion: bool = False,
    ) -> None:
        super().__init__(parent)
        self._snapshot = snapshot
        self._background = QColor(background)
        self._progress = 0.0
        self._fragments = self._make_fragments()
        self.setGeometry(geometry)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)
        self.show()
        self.raise_()

        self._animation = QVariantAnimation(self)
        self._animation.setStartValue(0.0)
        self._animation.setEndValue(1.0)
        self._animation.setDuration(220 if reduced_motion else 620)
        self._animation.valueChanged.connect(self._update_progress)
        self._animation.finished.connect(self.deleteLater)
        self._animation.start()

    def _make_fragments(self) -> list[_Fragment]:
        logical_size = self._snapshot.deviceIndependentSize()
        width, height = round(logical_size.width()), round(logical_size.height())
        if width <= 0 or height <= 0:
            return []

        columns = min(22, max(10, round(width / 54)))
        rows = min(16, max(8, round(height / 48)))
        rng = random.Random()
        vertices = [
            [
                QPointF(
                    column * width / columns
                    + (
                        rng.uniform(-0.16, 0.16) * width / columns
                        if 0 < column < columns
                        else 0
                    ),
                    row * height / rows
                    + (
                        rng.uniform(-0.16, 0.16) * height / rows
                        if 0 < row < rows
                        else 0
                    ),
                )
                for column in range(columns + 1)
            ]
            for row in range(rows + 1)
        ]
        center_x, center_y = width / 2, height / 2
        fragments = []
        for row in range(rows):
            for column in range(columns):
                corners = (
                    vertices[row][column],
                    vertices[row][column + 1],
                    vertices[row + 1][column + 1],
                    vertices[row + 1][column],
                )
                path = QPainterPath(corners[0])
                for corner in corners[1:]:
                    path.lineTo(corner)
                path.closeSubpath()
                center = QPointF(
                    sum(point.x() for point in corners) / 4,
                    sum(point.y() for point in corners) / 4,
                )
                vector_x = center.x() - center_x
                vector_y = center.y() - center_y
                length = max(1.0, math.hypot(vector_x, vector_y))
                distance = rng.uniform(30, 125)
                fragments.append(
                    _Fragment(
                        path=path,
                        center=center,
                        dx=vector_x / length * distance + rng.uniform(-20, 20),
                        dy=vector_y / length * distance + rng.uniform(4, 30),
                        rotation=rng.uniform(-13, 13),
                        scale=rng.uniform(0.78, 0.97),
                        delay=rng.uniform(0, 0.12),
                    )
                )
        return fragments

    def _update_progress(self, value) -> None:
        self._progress = float(value)
        self.update()

    def paintEvent(self, _event) -> None:
        if self._snapshot.isNull():
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), self._background)
        for fragment in self._fragments:
            local_progress = (self._progress - fragment.delay) / (1 - fragment.delay)
            if local_progress <= 0:
                eased = 0.0
                opacity = 1.0
            else:
                local_progress = min(1.0, local_progress)
                eased = 1 - (1 - local_progress) ** 3
                fade = max(0.0, min(1.0, (local_progress - 0.18) / 0.82))
                opacity = 1 - fade * fade * (3 - 2 * fade)

            painter.save()
            painter.setOpacity(opacity)
            painter.translate(
                fragment.center.x() + fragment.dx * eased,
                fragment.center.y() + fragment.dy * eased,
            )
            painter.rotate(fragment.rotation * eased)
            scale = 1 - (1 - fragment.scale) * eased
            painter.scale(scale, scale)
            painter.translate(-fragment.center.x(), -fragment.center.y())
            painter.setClipPath(fragment.path)
            painter.drawPixmap(0, 0, self._snapshot)
            painter.restore()
        painter.end()
