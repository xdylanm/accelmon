import sys
sys.path.append('../src/accelmon')

import logging
import threading
import time
import argparse
import board
from sinks import CsvSampleSink, SignedInt16Converter, NoConversionConverter

if __name__ == "__main__":
    format = "%(asctime)s: %(message)s"
    logging.basicConfig(format=format, level=logging.INFO, datefmt="%H:%M:%S")
    
    parser = argparse.ArgumentParser(description='Read SAMD21 ADC over serial')
    parser.add_argument('-m','--max-count', type=int, default=0,  
            help='Maximum number of samples to record. Default 0 (no maximum)')
    parser.add_argument('-t','--timeout', type=int, default=0,  
            help='Collection time for sampling (s). Default is 0 (no timeout)')
    parser.add_argument('-p', '--port', default='/dev/ttyACM0',  
            help='Serial port name. Default is /dev/ttyACM0.')
    parser.add_argument('filename', help='CSV file for data output')
    args = parser.parse_args()

    logging.info("Starting demo")
    logging.info(args)
    
    peek = board.Controller(port=args.port)
    b_id, accel_type = peek.board_id()
    logging.info(f"Board ID: {b_id}, Accelerometer: {accel_type}")
    
    values_per_conversion = 3 if accel_type == "KX134" else 1

    converter=NoConversionConverter()
    if accel_type == "KX134":
        gsel = peek.accel_g_range
        gscaling = 1./(2**(15 - (3 + gsel)))
        converter = SignedInt16Converter(scaling=gscaling) 

    logging.info("Creating sink {}".format(args.filename))
    csv = CsvSampleSink(args.filename, width=values_per_conversion, converter=converter)
    csv.open()
    
    mon = board.Controller(port=args.port, sinks=[csv])

    logging.info("Main: creating thread")
    x = threading.Thread(target=mon.collect_samples, args=(args.max_count,))
    logging.info("Main: starting thread")
    x.start()
    
    t = threading.Timer(args.timeout, mon.stop_collection)
    if args.timeout > 0:
        t.start()

    heartbeat = 0
    while x.is_alive():
        heartbeat += 1
        logging.info("..{}".format(heartbeat))
        time.sleep(1.)

    # here either the timer expired and called halt or we processed 
    # max_steps messages and exited
    logging.info("Main: cancel timer")
    t.cancel()
    logging.info("Main: calling join")
    x.join()
    logging.info("Main: closing sink")
    csv.close()
    logging.info("Main: done")

    n_samples = mon.sample_count() 
    n_dropped = mon.dropped_count()

    print(f"Collected {n_samples} samples with {n_dropped} dropped")




