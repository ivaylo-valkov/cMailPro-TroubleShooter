#!/usr/bin/perl

use strict;
use warnings;

use lib qw(. /usr/local/cpanel/3rdparty/perl/514/lib64/perl5/cpanel_lib/);

use CGI;
use JSON;
use File::Find::Rule;
use File::Slurp;
use File::Basename;
use Path::Class;

our $VERSION = '0.4';
our $NAME = 'cMailPro TroubleShooter CG helper API';

our $queue_dir = "/var/CommuniGate/Queue/";
our $logs_dir = "/var/CommuniGate/SystemLogs/";

sub main {
    my $q = CGI->new;

    my $remote_addr = $q->remote_addr();
    if ($remote_addr ne '[127.0.0.1]' && 
	$remote_addr ne '[77.71.117.10]') {
	return;
    }

    my @captured;
    my $render_data ; 
    my $path = $q->path_info;

    if (!$path || $path =~ m/^\/$/) {
	$render_data = { api => $NAME, api_version => $VERSION }; 
    } elsif ($path =~ m/messages(\/)*$/) {
	$render_data = messages();
    } elsif (@captured = $path =~ m/messages\/(.*)$/) {
	my $message = $captured[0];

	$render_data = message($message);
    } elsif (@captured = $path =~ m/message_exists\/(.*)$/) {
	my $message = $captured[0];

	$render_data = message_exists($message);
    } elsif ($path =~ m/message_count$/) {
	$render_data = message_count();
    } elsif ($path =~ m/logs\/topics$/ || $path =~ m/logs(\/)*$/) {
	$render_data = logs_topics();
    } elsif (@captured = $path =~ m/logs\/by_topic\/(.*)$/) {
	my $topic = $captured[0];

	$render_data = logs_by_topic($topic);
    } elsif (@captured = $path =~ m/logs\/file\/(.*)$/) {
	my $log = $captured[0];

	$render_data = logs_file($log);
    } elsif (@captured = $path =~ m/logs\/count\/(.*)$/) {
	my $topic = $captured[0];

	$render_data = logs_count($topic);
    }

    render($q, $render_data);
}

# https://IP:port/cgi/this.cgi/message_exists/<msg_id>
sub message_exists {
    my $message = shift;
    my $json  = { message_exists => 0 };

    my @file = File::Find::Rule->file()->name($message.".msg")->in($queue_dir);
    if ($file[0]) {
	$json->{message_exists} = 1;
    }

    return $json;
}


# https://IP:port/cgi/this.cgi/messages/<msg_id>
sub message {
    my $message = shift;

    my @file = File::Find::Rule->file()->name($message.".msg")->in($queue_dir);
    if ($file[0]) {
	my @data = read_file($file[0], binmode => ':utf8');

	return { message => \@data };
    }

    return {};
}

# https://IP:port/cgi/this.cgi/message_count
sub message_count {

    my @files = sort(File::Find::Rule->file()->name("*.msg")->in($queue_dir));
    my $count = scalar(@files);

    return { message_count => $count };
}

# https://IP:port/cgi/this.cgi/messages
sub messages {

    my @files = sort(File::Find::Rule->file()->name("*.msg")->in($queue_dir));
    my @messages;

    foreach my $f (@files) {
	my ($from, $to, $subject, $date);

	open (my $FH, "<", $f);

	if ($FH) {

	    my $count = 0;

	    while (my $line = <$FH>) {
		$count++;
		chomp $line;
		my @captures = $line =~ m/^Subject:(.*)/;

		$subject = $captures[0] unless !$captures[0];

		@captures = $line =~ m/^From:(.*)/;
		$from = $captures[0]  unless !$captures[0];
	

		@captures = $line =~ m/^To:(.*)/;
		$to = $captures[0]  unless !$captures[0];

		@captures = $line =~ m/^Date:(.*)/;
		$date = $captures[0]  unless !$captures[0];

		if ($count >= 30 || 
		    ($to && $from && $subject && $date)) {
		    last;
		}
	    }
	    
	    close($FH);
	}

	$f =~ s/$queue_dir//;
	$f =~ s/\.msg//;

	push @messages, { 
	    date => $date,
	    id => $f,
	    to => $to,
	    from => $from,
	    subject => $subject
	};
    }

    return { messages => \@messages };
}


# https://IP:port/cgi/this.cgi/logs/topics
sub logs_topics {

    my @dirs = sort(File::Find::Rule->directory->in($logs_dir));
    my @topics;

    foreach my $d (@dirs) {

	if ($d eq $logs_dir || ($d."/") eq $logs_dir) {
	    $d = "SystemLogs";
	}

	$d =~ s/$logs_dir//;

	push @topics, $d
    }


    return { logs => { topics  => \@topics } };
}

# https://IP:port/cgi/this.cgi/logs/by_topic
sub logs_by_topic {
    my $topic = shift;
    my $json = {};
    my @dir;

    if ( $topic eq 'SystemLogs') {
	push @dir, $logs_dir;
    } else {
	@dir = File::Find::Rule->directory()->name($topic)->in($logs_dir);
    }

    my @logs;

    if ($dir[0]) {
	my @files = sort(File::Find::Rule->file->name("*.log")->maxdepth(1)->in($dir[0]));

	for my $f ( @files ) {
	    $f =~ s/$logs_dir//;
	    push @logs, $f;
	}

	$json = { logs => { by_topic => { topic => $topic, logs => \@logs } } };
    }

    return $json;

}

# https://IP:port/cgi/this.cgi/logs/file/<filename>
sub logs_file {
    my $file = shift;
    my $json  = { };

    my $dir = dirname($file);
    $file = basename($file);

    if ($dir ne '.') {
	$dir = dir($logs_dir, $dir) ;
    } else {
	$dir = $logs_dir;
    }

    my @file = File::Find::Rule->file()->name($file)->in($dir);
    if ($file[0]) {
	my @data = read_file($file[0], binmode => ':utf8');

	$json = { logs => { file => \@data } };
    }

    return $json;
}


# https://IP:port/cgi/this.cgi/logs/count/<topic>
sub logs_count {
    my $topic = shift;
    my $dir = $logs_dir;
    my $depth = 3;

    if ($topic && $topic eq 'SystemLogs') {
	$depth = 1;
    } elsif ($topic) {
	$dir = dir($logs_dir, $topic);
    }

    my @files = File::Find::Rule->file()->name("*.log")->maxdepth($depth)->in($dir);

    return { logs => { count => { topic => $topic, count => scalar(@files) } } } ;

}

sub render {
    my $q = shift;
    my $render = shift || {  };

    print $q->header(-type=> "application/json", -charset=>"UTF-8");   

    printf to_json($render);
    printf "\n";
}

main();

