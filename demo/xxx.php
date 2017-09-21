<?php
$type = $_SERVER['argv'][1];
$file = $_SERVER['argv'][2];

try {
    $data = @file_get_contents($file);
    if(!$data) {
        response(false);
    }

    $data = json_decode($data, true);
    if(!$data) {
        response(false);
    }

    if($type == 'db_master') {
        $config = require (__DIR__ . '/database.php');
        $config['connections']['default']['write']['host'] = $data['host'];
        $config['connections']['default']['write']['port'] = $data['port'];
        $config['connections']['default']['write']['database'] = $data['database'];
        $config['connections']['default']['write']['username'] = $data['username'];
        $config['connections']['default']['write']['password'] = $data['password'];
        $config['connections']['default']['charset'] = $data['charset'];
        $config['connections']['default']['collation'] = $data['collation'];
        $config['connections']['default']['prefix'] = $data['prefix'];
        $config['connections']['default']['timezone'] = $data['timezone'];

        $phpcode = var_export($config, true);
        file_put_contents(__DIR__ . '/database.php', '<?php return ' . $phpcode . ';');
    } elseif($type == 'db_slave') {
        $config = require (__DIR__ . '/database.php');
        $config['connections']['default']['read']['host'] = $data['host'];
        $config['connections']['default']['read']['port'] = $data['port'];
        $config['connections']['default']['read']['database'] = $data['database'];
        $config['connections']['default']['read']['username'] = $data['username'];
        $config['connections']['default']['read']['password'] = $data['password'];
        $config['connections']['default']['charset'] = $data['charset'];
        $config['connections']['default']['collation'] = $data['collation'];
        $config['connections']['default']['prefix'] = $data['prefix'];
        $config['connections']['default']['timezone'] = $data['timezone'];

        $phpcode = var_export($config, true);
        file_put_contents(__DIR__ . '/database.php', '<?php return ' . $phpcode . ';');
    } elseif($type == 'db_56gamebbs_master') {
        $config = require (__DIR__ . '/database.php');
        $config['connections']['56gamebbs']['write']['host'] = $data['host'];
        $config['connections']['56gamebbs']['write']['port'] = $data['port'];
        $config['connections']['56gamebbs']['write']['database'] = $data['database'];
        $config['connections']['56gamebbs']['write']['username'] = $data['username'];
        $config['connections']['56gamebbs']['write']['password'] = $data['password'];
        $config['connections']['56gamebbs']['charset'] = $data['charset'];
        $config['connections']['56gamebbs']['collation'] = $data['collation'];
        $config['connections']['56gamebbs']['prefix'] = $data['prefix'];
        $config['connections']['56gamebbs']['timezone'] = $data['timezone'];

        $phpcode = var_export($config, true);
        file_put_contents(__DIR__ . '/database.php', '<?php return ' . $phpcode . ';');
    } elseif($type == 'db_56gamebbs_slave') {
        $config = require (__DIR__ . '/database.php');
        $config['connections']['56gamebbs']['read']['host'] = $data['host'];
        $config['connections']['56gamebbs']['read']['port'] = $data['port'];
        $config['connections']['56gamebbs']['read']['database'] = $data['database'];
        $config['connections']['56gamebbs']['read']['username'] = $data['username'];
        $config['connections']['56gamebbs']['read']['password'] = $data['password'];
        $config['connections']['56gamebbs']['charset'] = $data['charset'];
        $config['connections']['56gamebbs']['collation'] = $data['collation'];
        $config['connections']['56gamebbs']['prefix'] = $data['prefix'];
        $config['connections']['56gamebbs']['timezone'] = $data['timezone'];

        $phpcode = var_export($config, true);
        file_put_contents(__DIR__ . '/database.php', '<?php return ' . $phpcode . ';');
    } elseif($type == 'mongodb_user_messages') {
        $config = require (__DIR__ . '/database.php');
        $config['connections']['mongodb']['host'] = $data['host'];
        $config['connections']['mongodb']['port'] = $data['port'];
        $config['connections']['mongodb']['database'] = $data['database'];
        $config['connections']['mongodb']['username'] = $data['username'];
        $config['connections']['mongodb']['password'] = $data['password'];
        $config['connections']['mongodb']['options']['database'] = $data['options']['database'];

        $phpcode = var_export($config, true);
        file_put_contents(__DIR__ . '/database.php', '<?php return ' . $phpcode . ';');
    } elseif($type == 'mongodb_logs') {
        $config = require (__DIR__ . '/database.php');
        $config['connections']['log']['host'] = $data['host'];
        $config['connections']['log']['port'] = $data['port'];
        $config['connections']['log']['database'] = $data['database'];
        $config['connections']['log']['username'] = $data['username'];
        $config['connections']['log']['password'] = $data['password'];
        $config['connections']['log']['options']['database'] = $data['options']['database'];

        $phpcode = var_export($config, true);
        file_put_contents(__DIR__ . '/database.php', '<?php return ' . $phpcode . ';');
    } elseif($type == 'redis_default') {
        $config = require (__DIR__ . '/database.php');
        $config['redis']['default']['host'] = $data['host'];
        $config['redis']['default']['port'] = $data['port'];
        $config['redis']['default']['database'] = $data['database'];
        $config['redis']['default']['password'] = $data['password'];
        $config['redis']['default']['prefix'] = $data['prefix'];

        $phpcode = var_export($config, true);
        file_put_contents(__DIR__ . '/database.php', '<?php return ' . $phpcode . ';');
    } else {
        response(false);
    }
    
    response(true);
} catch(Exception $e) {
    response(false);
}

function response($is_success) {
    if($is_success) {
        echo 'SUCCESS';
        exit(0);
    } else {
        echo 'FAIL';
        exit(1);
    }
}