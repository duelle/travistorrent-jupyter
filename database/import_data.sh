

#mysql -p -u root -h 127.0.0.1 -P 3306 travistorrent < tt_aggregated.sql

#mysql -p -u root -h 127.0.0.1 -P 3306 


CREATE TABLE `tt_build_data` (
  `build_id` bigint(20) NOT NULL,
  `job_id` bigint(20) NOT NULL,
  `build_number` int(11) NOT NULL,
  `original_commit` varchar(40) NOT NULL CHARACTER SET utf8,
  `log_setup_time` int(11) DEFAULT NULL,
  PRIMARY KEY (`job_id`),
  UNIQUE KEY (`build_id`),
  UNIQUE KEY (`original_commit`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

CREATE TABLE `tt_repo_data` (
  `build_id` bigint(20) NOT NULL,
  `commit_hash` varchar(40) DEFAULT NULL,
  `pull_req` int(11) DEFAULT NULL,
  `branch` varchar(100) CHARACTER SET utf8 DEFAULT NULL,
  `status` varchar(50) CHARACTER SET utf8 DEFAULT NULL,
  `duration` int(11) DEFAULT NULL,
  `started_at` datetime NOT NULL,
  `job_list` varchar(200) CHARACTER SET utf8 DEFAULT NULL,
  `event_type` varchar(100) CHARACTER SET utf8 DEFAULT NULL,
  PRIMARY KEY (`build_id`),
  UNIQUE KEY (`commit_hash`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

CREATE TABLE `tt_extracted_data` (
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
