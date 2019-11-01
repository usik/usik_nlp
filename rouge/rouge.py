# coding=utf-8

'''
    This code calculates ROUGE scores.
    Output is in CSV formatted text file.

    Example:
        rouge ---rouge_types = rouge1, rouge2, rougeL \
        --target_filepattern=*.targets \
        --prediction_filepattern=*.decodes \
        --output_filename= scores.csv \
        --use_stemmer
'''
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from absl import app
from absl import flags
from rouge import io
from rouge import rouge_scorer
from rouge import scoring

flags.DEFINE_string("target_filepattern", None,
                    "Files containing target text.")
flags.DEFINE_string("prediction_filepattern", None,
                    "Files containing prediction text.")
flags.DEFINE_string("output_filename", None,
                    "File in which to write calculated ROUGE scores as a CSV.")
flags.DEFINE_string("delimiter", "\n",
                    "Record delimiter  in files.")
flags.DEFINE_list("rouge_types", ["rouge1", "rouge2", "rougeL"],
                  "List of ROUGE types to calculate.")
flags.DEFINE_boolean("use_stemmer", False,
                     "Whether to use Porter stemmer to remove common suffixes.")
flags.DEFINE_boolean("aggregate", True,
                     "Write aggregates if this is set to True")

FLAGS = flags.FLAGS


def main(argv):
  if len(argv) > 1:
    raise app.UsageError("Too many command-line arguments.")

  scorer = rouge_scorer.RougeScorer(FLAGS.rouge_types, FLAGS.use_stemmer)
  aggregator = scoring.BootstrapAggregator() if FLAGS.aggregate else None
  io.compute_scores_and_write_to_csv(
      FLAGS.target_filepattern,
      FLAGS.prediction_filepattern,
      FLAGS.output_filename,
      scorer,
      aggregator,
      delimiter=FLAGS.delimiter)


if __name__ == "__main__":
  flags.mark_flag_as_required("target_filepattern")
  flags.mark_flag_as_required("prediction_filepattern")
  flags.mark_flag_as_required("output_filename")
  app.run(main)
