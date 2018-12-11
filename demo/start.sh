ps -ef | grep 'af-conf.py' | awk '{print $2}' | xargs kill -9

python ../af-conf.py 127.0.0.1.conf > 127.0.0.1.log &
python ../af-conf.py 127.0.0.2.conf > 127.0.0.2.log &
python ../af-conf.py 127.0.0.3.conf > 127.0.0.3.log &
python ../af-conf.py 127.0.0.4.conf > 127.0.0.4.log &
python ../af-conf.py 127.0.0.5.conf > 127.0.0.5.log &
python ../af-conf.py 127.0.0.6.conf > 127.0.0.6.log &
python ../af-conf.py 127.0.0.7.conf > 127.0.0.7.log &
python ../af-conf.py 127.0.0.8.conf > 127.0.0.8.log &