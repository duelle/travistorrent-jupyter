library('R.utils')
library('data.table')

setwd("/home/duelle/Repositories/git/travistorrent-jupyter/")

tt <- fread("travistorrent_8_2_2017.csv")

tt <- tt[tt$tr_duration != "NA"]
tt <- tt[, c("tr_build_id","git_branch","gh_project_name","gh_build_started_at","tr_duration")]
tt <- tt[!duplicated(tt$tr_build_id),]

# Assign start and duration to variables
tt_start <- tt$gh_build_started_at
tt_duration<- tt$tr_duration

# Extract epoch formats for start and end by adding duration to start
tt_start_epoch <- as.POSIXct(tt_start ,format="%Y-%m-%d %H:%M")
tt_end_epoch <- tt_start_epoch + tt_duration
#tt_end_epoch <- as.POSIXct(as.POSIXlt(tt_end_epoch), format="%Y-%m-%d %H:%M")
tt_end_epoch <- strptime(tt_end_epoch, "%Y-%m-%d %H:%M")

# Find min and max time
time_min <- min(tt_start_epoch)
time_max <- max(as.POSIXct(tt_end_epoch))

options(digits.secs=0)
queries.start <- data.frame(Time=tt_start_epoch, Value=1)
queries.end <- data.frame(Time=tt_end_epoch, Value=-1)

#queries.both <- rbind(queries.start[1:500,], queries.end[1:500,])
queries.both <- rbind(queries.start, queries.end)
queries.both <- queries.both[with(queries.both, order(Time)), ]

queries.sum <- data.frame(Time=queries.both$Time, Queries=cumsum(queries.both$Value))

queries.param <- c(0,queries.sum$Queries)
queries.steps <- stepfun(queries.sum$Time, queries.param)

exp_data <- queries.steps(time_min:time_max)

plot(exp_data, type="p")

#write.csv()