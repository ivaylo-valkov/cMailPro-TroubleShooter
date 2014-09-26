package cMailPro::TroubleShooter::Controller::Logs;
use Moose;
use namespace::autoclean;

BEGIN {extends 'Catalyst::Controller'; }

=head1 NAME

cMailPro::TroubleShooter::Controller::Logs - Catalyst Controller

=head1 DESCRIPTION

Catalyst Controller.

=head1 METHODS

=cut


=head2 index

  List log topics/directories.

=cut

sub index :Path :Args(0) {
    my ( $self, $c ) = @_;
    use Data::Dumper;

    my $cg_ts_api = new $c->model('CommuniGate::cMailProTSAPI');
    my $topics = $cg_ts_api->fetch('/logs/topics');
    my $overview = [];
    my $total_logs = 0;

    for my $t (@{$topics->{logs}->{topics}}) {
	$c->log->debug("T ".Dumper $t);
	my $count = $cg_ts_api->fetch('/logs/count/'.$t);
	$count = $count->{logs}->{count}->{count};
	push $overview, { topic => $t, logs => $count };
	$total_logs += $count;
    }

    $c->stash->{total_logs} = $total_logs;
    $c->stash->{logs_overview} = $overview;
}


=head2 topic

 List log files in topic/directory.

=cut

sub topic :LocalRegexp('^(?!(~.*$))topic/(.*)') {
    my ( $self, $c ) = @_;

    my $topic = $c->request->captures->[1];
    my $cg_ts_api = new $c->model('CommuniGate::cMailProTSAPI');
    my $topic_api = $cg_ts_api->fetch('/logs/by_topic/'. $topic);

    if ($topic_api && $topic_api->{logs}->{by_topic}) {
        $c->stash->{logs_by_topic} = $topic_api->{logs}->{by_topic}->{logs} ;
        $c->stash->{log_topic} = $topic_api->{logs}->{by_topic}->{topic} ;
    } else {
	$c->response->status(404);
	$c->stash->{error_msg} = [ "Topic " . $topic." not found" ];
    }

    if ( $topic_api->{error} ) {
	$c->response->status(500);
	$c->stash->{error_msg} = [ $topic_api->{error} ];
	$c->stash->{status_msg} = ["Internal Server Error. CGI API communication error."];
    }
}

=head2 file

 View and download log files

=cut

sub file :LocalRegexp("^(?!(~.*$))(file|download)/(.*)") {
    my ( $self, $c ) = @_;

    my $file = $c->request->captures->[2];
    my $rel_path = $c->request->captures->[1];

    my $cg_ts_api = new $c->model('CommuniGate::cMailProTSAPI');
    my $file_api = $cg_ts_api->fetch('/logs/file/'. $file);

    if ($file_api && $file_api->{logs}->{file}) {
	if ($rel_path eq 'download') {
	    $file =~ s/\//-/g;
	    $c->res->header('Content-Disposition', qq[attachment; filename="$file"]);
	    $c->res->content_type('text/plain');
	    $c->response->body (join("\n", @{$file_api->{logs}->{file}})) ;
	} else {
	    $c->stash->{log_file_contents} = $file_api->{logs}->{file} ;
	    $c->stash->{log_file} = $file;
	}
    } else {
	$c->response->status(404);
	$c->stash->{error_msg} = [ "File " . $file." not found" ];
    }

    if ( $file_api->{error} ) {
	$c->response->status(500);
	$c->stash->{error_msg} = [ $file_api->{error} ];
	$c->stash->{status_msg} = ["Internal Server Error. CGI API communication error."];
    }
}


=head1 AUTHOR

Ivaylo Valkov <ivaylo@e-valkov.org>

=head1 LICENSE

Awaiting contractor approval.

=cut

__PACKAGE__->meta->make_immutable;

1;
