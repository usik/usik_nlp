# coding=utf-8

"""
For creating files from {target,prediction}.txt that can be processed
by pyrouge to compare with scores in scoring_test.py.

  create_pyrouge_files -- --testdata_dir=`pwd`/testdata

  # testConfidenceIntervalsAgainstRouge155WithStemming result

  pyrouge_evaluate_plain_text_files \
      -s /tmp/lkj -sfp "prediction.(.*).txt" \
      -m /tmp/lkj -mfp target.#ID#.txt
"""

from __future__ import absolute_import
from __future__ import division

from __future__ import print_function

import os

from absl import app
from absl import flags

FLAGS = flags.FLAGS

flags.DEFINE_string('testdata_dir', '', 'testdata path')
flags.DEFINE_string('output',  '/tmp/lkj', 'testdata path')

def write_files(prefix, items):
    for i, t in enumerate(items):
        out = '%s.%d.txt' % (prefix, i)
        with open(os.path.join(FLAGS.output, out), 'w') as f:
            f.write(t)

def main(argv):
  if len(argv) > 1:
    raise app.UsageError('Too many command-line arguments.')

  # One line per target
  with open(os.path.join(FLAGS.testdata_dir, 'target_large.txt')) as f:
    targets = f.readlines()
  with open(os.path.join(FLAGS.testdata_dir, 'prediction_large.txt')) as f:
    predictions = f.readlines()

  write_files('target', targets)
  write_files('prediction', predictions)

if __name__ == '__main__':
  app.run(main)
