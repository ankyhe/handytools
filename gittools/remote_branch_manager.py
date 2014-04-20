#! /usr/bin/python

import curses
import re
import subprocess
import sys

REMOTE_BRANCH_INDEX_REMOVE_KEY = 'topic/hez'
REMOTE_BRANCH_INDEX_KEEP_KEY = '-keep'

class Branch(object):

  RE_SPACE = re.compile('\s+')

  def __init__(self, branch):
    arr = self.RE_SPACE.split(branch)
    arr.reverse()
    arr = [x.lstrip('/refs/heads/') for x in arr]
    self._branch = ' '.join(arr)
    self.select = False

  def toggle_select(self):
    if not self.branch_name.endswith(REMOTE_BRANCH_INDEX_KEEP_KEY):
      self.select = not self.select
    return self.select

  def __repr__(self):
    return str(self)

  def __str__(self):
    mark = '[ ]'
    if self.select:
      mark = '[x]'
    return '{0} {1}'.format(mark, self._branch)

  # property remote_branches
  def is_select(self): return self._select
  def set_select(self, select): self._select = select
  remote_branches = property(is_select, set_select, None, "I'm the 'select' property.")

  def get_branch_name(self): return self._branch.split(' ')[0]
  branch_name = property(get_branch_name, None, None, '')



class GitModel(object):

  def __init__(self):
    self._init_remote_branches()

  def _init_remote_branches(self):
    # Just use subprocess to call git, not use libgit2 due to I don't like cmake
    remote_branches = subprocess.check_output(['git', 'ls-remote'])
    remote_branches = remote_branches.split('\n')
    self._remote_branches = [Branch(x) for x in remote_branches if x.find(REMOTE_BRANCH_INDEX_REMOVE_KEY) != -1]
 
  def toggle(self, idx):
    if idx < 0 or idx >= len(self.remote_branches):
      pass # do nothing
    branch = self.remote_branches[idx]
    return branch.toggle_select()
 
  def __len__(self):
    return len(self.remote_branches)

  # property remote_branches
  def get_remote_branch(self): return self._remote_branches
  remote_branches = property(get_remote_branch, None, None, "")

  def get_select_num(self):
    sum = 0
    for branch in self.remote_branches:
      if branch.select:
        sum += 1
    return sum

  select_num = property(get_select_num, None, None, "")

  def get_all_select_branches(self):
    ret = [x for x in self.remote_branches if x.select]
    return ret

  all_select_branches = property(get_all_select_branches, None, None, '')


class Screen(object):

  UP = 0
  DOWN = 1

  def __init__(self):
    self._curLineNum = 0
    self._topLineNum = 0
    self._updateTimes = 0
    self._delete_confirm = False
    self._running = True
    self._exit_by_q = True
    self._git_model = GitModel()
    self._screen = curses.initscr()
    curses.start_color()
    curses.use_default_colors()
    curses.init_pair(1, curses.COLOR_WHITE, -1)
    curses.init_pair(2, curses.COLOR_RED, -1)
    curses.init_pair(3, curses.COLOR_BLACK, curses.COLOR_YELLOW)
    curses.init_pair(4, curses.COLOR_RED, curses.COLOR_YELLOW)
    curses.init_pair(5, curses.COLOR_GREEN, -1)
    curses.noecho()
    curses.cbreak()
    self._screen.keypad(True)

  def run(self):
    while self._running:
      self.updateScreen()
      c = self._screen.getch()
      if self._delete_confirm:
        if c == ord('a'): 
          self._delete_action()
        else:
          self._back_action()
      else:
        if c == curses.KEY_UP or c == ord('k'): 
          self._move_action(self.UP)
        elif c == curses.KEY_DOWN or c == ord('j'): 
          self._move_action(self.DOWN)
        elif c == ord(' ') or c == ord('s'): #select 
          self._select_action()
        elif c == ord('d'):
          self._delete_confirm_action()
      if c == ord('q'):
        self._running = False
        self._exit_by_q = True

    if not self._exit_by_q:
      self._restoreScreen()
      branches = self._git_model.all_select_branches
      branch_names = [x.branch_name for x in branches]
      for branch_name in branch_names:
        delete_branch_output = subprocess.check_output(['git', 'push', 'origin', ':{0}'.format(branch_name)])
        print (delete_branch_output)

  

  def __del__(self):
    self._restoreScreen();

  def _restoreScreen(self):
    curses.nocbreak()
    self._screen.keypad(False)
    curses.echo()
    curses.endwin()          
 
  def _move_action(self, direction):
    if direction == self.UP:
      self._curLineNum -= 1
    
    elif direction == self.DOWN:
      self._curLineNum += 1

    show_line_num = min(curses.LINES - 1, len(self._git_model))

    if self._curLineNum < 0:
      self._curLineNum = 0
    elif self._curLineNum > show_line_num - 1:
      if curses.LINES - 1 > len(self._git_model):
        self._curLineNum = len(self._git_model) - 1
      else:
        if self._curLineNum > len(self._git_model) - 1:
          self._curLineNum = len(self._git_model) - 1
      self._topLineNum = self._curLineNum - show_line_num + 1
    else: # 
      self._topLineNum = 0
 
  def _select_action(self):
    self._git_model.toggle(self._curLineNum)

  def _delete_confirm_action(self):
    if self._git_model.select_num > 0:
      self._delete_confirm = True

  def _back_action(self):
    self._delete_confirm = False

  def _delete_action(self):
    self._exit_by_q = False
    self._running = False
    
      
  def updateScreen(self):
    self._updateTimes += 1
    self._screen.erase()
    show_line_num = min(curses.LINES - 1, len(self._git_model))
    for idx in range(self._topLineNum, show_line_num + self._topLineNum):
      remote_branch = self._git_model.remote_branches[idx]
      cp = curses.color_pair(1)
      if idx == self._curLineNum:
        if remote_branch.select:
          cp = curses.color_pair(4)
        else:
          cp = curses.color_pair(3)
      else:
        if remote_branch.select:
          cp = curses.color_pair(2)
        else:
          cp = curses.color_pair(1)
      self._screen.addstr(idx - self._topLineNum, 0, '{0}'.format(remote_branch), cp)
    if self._delete_confirm:
      self._screen.addstr(show_line_num, 0, 'Help exit:[q] accept:[a] abort:[other keys] | Info: Number:[{0}]'.format(self._git_model.select_num), curses.color_pair(5))
    else:
      self._screen.addstr(show_line_num, 0, 'Help exit:[q] down:[j] up:[k] select:[SPACE]', curses.color_pair(5))
    if self._curLineNum > show_line_num - 1:
      self._screen.move(show_line_num - 1, 0)
    else:
      self._screen.move(self._curLineNum, 0)
    self._screen.refresh()


def main():
  Screen().run()

if __name__ == '__main__':
  main()

