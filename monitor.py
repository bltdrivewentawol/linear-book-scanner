#!/usr/bin/python2.6
#
# Copyright 2011 Google Inc. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
import glob
import time
import pygame
import sys
import os.path
import subprocess
import urllib

def blue():
  """Original scansation blue, handed down from antiquity"""
  return (70, 120, 173)

def clearscreen(screen):
  """And G-d said, "Let there be light!"""
  background = pygame.Surface(screen.get_size())
  background = background.convert()
  background.fill(blue())
  screen.blit(background, (0,0))

def render_text(screen, text, position):
  """Write messages to screen, such as the image number"""
  font = pygame.font.SysFont('Courier', 28, bold=True)
  text = font.render(text, 1, (255, 255, 255))
  background = pygame.Surface(text.get_size())
  background = background.convert()
  background.fill(blue())
  if position == "upperleft":
    pos = (0, 0)
  elif position == "upperright":
    pos = (screen.get_width() - text.get_width(), 0)
  elif position == "center":
    pos = (screen.get_width() // 2 - text.get_width() // 2,
           screen.get_height() // 2)
  screen.blit(background, pos)
  screen.blit(text, pos)

def process_images(h, filename_a, filename_b):
  """Crop out the saddle, and reverse one of the sensors.
  Returns both screen size and full size images."""
  kSaddleHeight = 3600
  kSensorOffsetA = 700
  kSensorOffsetB = 300
  image_a = pygame.image.load(filename_a)
  image_b = pygame.image.load(filename_b)
  crop_a = pygame.Surface((image_a.get_width(), kSaddleHeight))
  crop_b = pygame.Surface((image_b.get_width(), kSaddleHeight))
  crop_a.blit(image_a, (0, 0), (0,
                                kSensorOffsetA,
                                crop_a.get_width(),
                                crop_a.get_height()))
  crop_b.blit(image_b, (0, 0), (0,
                                kSensorOffsetB,
                                crop_b.get_width(),
                                crop_b.get_height()))
  crop_a = pygame.transform.flip(crop_a, True, False)
  w_prime = image_a.get_width() * h / kSaddleHeight
  surface_a = pygame.transform.smoothscale(crop_a, (w_prime, h))
  surface_b = pygame.transform.smoothscale(crop_b, (w_prime, h))
  return surface_a, surface_b, crop_a, crop_b

def handle_user_input():
  """ F11 drops us out of full screen mode.
      ESC or Q quits the program
      Mouseclick creats a zoombox while mouse is down"""
  pos = None
  screen = None
  for event in pygame.event.get():
    if event.type == pygame.MOUSEBUTTONDOWN:
      if event.button == 1:
        pos = event.pos
    elif event.type == pygame.QUIT:
      pygame.quit()
      sys.exit()
    elif (event.type == pygame.KEYDOWN):
      if event.key == pygame.K_ESCAPE or event.key == pygame.K_q:
        pygame.quit()
        sys.exit()
      elif event.key == pygame.K_F11:
        h = pygame.display.Info().current_h
        w = pygame.display.Info().current_w
        window = pygame.display.set_mode((w, h))
        screen = pygame.display.get_surface()
  return pos, screen

def wait_for_mouseup():
  while True:
    for event in pygame.event.get():
      if event.type == pygame.MOUSEBUTTONUP:
        return

def zoombox(screen, click, surface, crop, surface_x0):
  """Help function created during refactoring. Draws the actual zoombox"""
  w = pygame.display.Info().current_w
  kZoomSize = w / 3
  zoombox_pos = (click[0] - kZoomSize, click[1] - kZoomSize)
  x = click[0] - surface_x0
  x = x * crop.get_width() // surface.get_width()
  y = click[1] * crop.get_height() // surface.get_height()
  if x < 0 or x >= crop.get_width():
    return
  screen.blit(crop, zoombox_pos,
              (x - kZoomSize, y - kZoomSize, 2 * kZoomSize, 2 * kZoomSize))

def zoom(screen, click, epsilon, surface_a, surface_b, crop_a, crop_b):
  """Given a mouseclick, zoom in on the region."""
  w = pygame.display.Info().current_w
  kZoomSize = w / 3
  zoombox_pos = (click[0] - kZoomSize, click[1] - kZoomSize)
  if click[0] < w // 2:
    surface_x0 = w // 2 - epsilon - surface_a.get_width()
    zoombox(screen, click, surface_a, crop_a, surface_x0)
  else:
    surface_x0 = w // 2 + epsilon
    zoombox(screen, click, surface_b, crop_b, surface_x0)

def draw(screen, image_number, surface_a, surface_b, epsilon):
  """Draw the page images and labels on screen for a given page pair."""
  w = pygame.display.Info().current_w
  clearscreen(screen)
  render_text(screen, str(image_number), "upperleft")
  render_text(screen, str(image_number + 1), "upperright")
  screen.blit(surface_a, (w // 2 - surface_a.get_width() - epsilon, 0))
  screen.blit(surface_b, (w // 2 + epsilon, 0))

def get_bibliography(barcode):
  """Hit up Google Books for bibliographic data. Thanks, Leonid."""
  if barcode[0:3] == "978":
    url = ("http://books.google.com/books/download/"
           "?vid=isbn%s&output=enw&source=cheese" % barcode[0:13])
    try:
      bib = urllib.urlopen(url).read()
    except IOError:
      return "Error looking up barcode: %s" % barcode.split("_")[0]
    print bib
    for line in bib.split("\n"):
      if line[0:2] == "%T":
        return line[3:].strip()
  return "Unknown Barcode: %s" % barcode.split("_")[0]

def main(barcode):
  """Monitor the scanning for images and display them."""
  pygame.init()
  image_number = 1
  playground = "/var/tmp/playground/%s" % barcode
  beep = pygame.mixer.Sound('beep.wav')
  h = pygame.display.Info().current_h
  w = pygame.display.Info().current_w
  epsilon = w // 100
  window = pygame.display.set_mode((w, h), pygame.FULLSCREEN)
  screen = pygame.display.get_surface()
  pygame.display.set_caption("Barcode: %s" % barcode)
  clearscreen(screen)
  render_text(screen, get_bibliography(barcode), "center")
  pygame.display.update()
  while True:
    time.sleep(0.2)
    click, newscreen = handle_user_input()
    if newscreen:
      screen = newscreen
    if click:
      image_number -= 2   # Helps redraw on mousedown
      draw(screen, image_number, surface_a, surface_b, epsilon)
      zoom(screen, click, epsilon, surface_a, surface_b, crop_a, crop_b)
      pygame.display.update()
      wait_for_mouseup()
    filename_a = '%s/%06d.pnm' % (playground, image_number)
    filename_b = '%s/%06d.pnm' % (playground, image_number + 1)
    try:
      surface_a, surface_b, crop_a, crop_b = process_images(h, filename_a,
                                                            filename_b)
    except pygame.error:
      continue
    draw(screen, image_number, surface_a, surface_b, epsilon)
    pygame.display.update()
    beep.play()
    image_number += 2

if __name__ == "__main__":
  main(sys.argv[1])
