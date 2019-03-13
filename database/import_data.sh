

#mysql -p -u root -h 127.0.0.1 -P 3306 travistorrent < tt_aggregated.sql

#mysql -p -u root -h 127.0.0.1 -P 3306 


CREATE TABLE `tt_build_data` (
  `build_id` bigint(20) NOT NULL,
  `job_id` bigint(20) NOT NULL,
  `build_number` int(11) NOT NULL,
  `original_commit` varchar(40) NOT NULL,
  `log_setup_time` int(11) DEFAULT NULL,
  PRIMARY KEY (`job_id`),
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

CREATE TABLE `tt_repo_data` (
  `build_id` bigint(20) NOT NULL,
  `commit_hash` varchar(40) DEFAULT NULL,
  `pull_req` int(11) DEFAULT NULL,
  `branch` varchar(100) CHARACTER SET utf8 DEFAULT NULL,
  `status` varchar(50) CHARACTER SET utf8 DEFAULT NULL,
  `duration` int(11) DEFAULT NULL,
  `started_at` datetime DEFAULT NULL,
  `job_list` longtext CHARACTER SET utf8 DEFAULT NULL,
  `event_type` varchar(100) CHARACTER SET utf8 DEFAULT NULL,
  PRIMARY KEY (`build_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

CREATE TABLE `tt_extracted_data` (
  `build_number` int(11) NOT NULL,
  `build_id`,
  `project`,
  `commit_hash`,
  `job_id`,
  `startup_duration_seconds`,
  `step_first_start_timestamp`,
  `step_last_end_timestamp`,
  `duration_diff_timestamp`,
  `duration_aggregated_timestamp`,
  `worker_hostname`
  `worker_version`,
  `worker_instance`,
  `os_dist_id`,
  `os_description`,
  `os_dist_release`,
  PRIMARY KEY (`build_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
