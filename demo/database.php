<?php return array (
  'default' => 'default',
  'connections' => 
  array (
    'default' => 
    array (
      'driver' => 'mysql',
      'read' => 
      array (
        'host' => '127.0.0.1',
        'port' => '3306',
        'database' => 'anfanapi',
        'username' => 'root',
        'password' => 'root',
      ),
      'write' => 
      array (
        'host' => '127.0.0.1',
        'port' => '3306',
        'database' => 'anfanapi',
        'username' => 'root',
        'password' => 'root',
      ),
      'charset' => 'utf8',
      'collation' => 'utf8_unicode_ci',
      'prefix' => '',
      'timezone' => '+00:00',
      'strict' => false,
    ),
    '56gamebbs' => 
    array (
      'driver' => 'mysql',
      'read' => 
      array (
        'host' => '127.0.0.1',
        'port' => '3306',
        'database' => '56gamebbs',
        'username' => 'root',
        'password' => 'root',
      ),
      'write' => 
      array (
        'host' => '127.0.0.1',
        'port' => '3306',
        'database' => '56gamebbs',
        'username' => 'root',
        'password' => 'root',
      ),
      'charset' => 'utf8',
      'collation' => 'utf8_unicode_ci',
      'prefix' => '',
      'timezone' => '+00:00',
      'strict' => false,
    ),
    'mongodb' => 
    array (
      'driver' => 'mongodb',
      'host' => '127.0.0.1',
      'port' => '27017',
      'database' => 'users_message',
      'username' => '',
      'password' => '',
      'options' => 
      array (
        'database' => 'users_message',
      ),
    ),
    'log' => 
    array (
      'driver' => 'mongodb',
      'host' => '127.0.0.1',
      'port' => '27017',
      'database' => 'log',
      'username' => '',
      'password' => '',
      'options' => 
      array (
        'database' => 'log',
      ),
    ),
  ),
  'migrations' => 'migrations',
  'redis' => 
  array (
    'cluster' => true,
    'default' => 
    array (
      'host' => '127.0.0.1',
      'port' => '6379',
      'database' => '0',
      'password' => '123456',
      'prefix' => NULL,
    ),
  ),
);