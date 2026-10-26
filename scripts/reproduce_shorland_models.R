# Source-formula/model-frame scrutiny, not Shiny reproduction or biological admission.
args <- commandArgs(TRUE)
.libPaths(c(args[3], .libPaths()))
library(lme4)
library(jsonlite)
Sys.umask('0077')
out <- args[4]
e <- new.env(parent=emptyenv())
load(args[2], envir=e)
d <- e$xdata
csv <- read.csv(args[1], check.names=FALSE)
shared <- intersect(names(csv), names(d))
stopifnot(nrow(d)==114L, nrow(csv)==114L,
  all(vapply(shared, function(k) isTRUE(all.equal(as.character(csv[[k]]),
    as.character(d[[k]]))), logical(1))),
  all(d$nolooktime == d$tottime-d$looktime),
  isTRUE(all.equal(d$logtottime,log1p(d$tottime))),
  all(d$explore == as.integer(d$peer | d$probe)))
stopifnot(length(unique(d$individual))==10L,
  length(unique(d$playbackID))==12L,
  nrow(unique(d[c('individual','playbackID')]))==57L,
  all(table(interaction(d$individual,d$playbackID,drop=TRUE))==2L))
warnings <- character()
fit <- function(x, endpoint, null=FALSE, optimizer=NULL) {
  rhs <- if(null) 'demoexposure + (1|individual) + (1|playbackID)' else
    'condition*location + demoexposure + (1|individual) + (1|playbackID)'
  response <- if(endpoint=='exploration') 'explore' else 'cbind(looktime,nolooktime)'
  f <- as.formula(paste(response,'~',rhs))
  a <- list(formula=f, data=x, family=binomial())
  if(endpoint=='exploration') a$offset <- x$logtottime
  if(!is.null(optimizer)) a$control <- glmerControl(optimizer=optimizer,
    optCtrl=list(maxfun=200000))
  withCallingHandlers(do.call(glmer,a), warning=function(w) {
    warnings <<- c(warnings,conditionMessage(w)); invokeRestart('muffleWarning')
  })
}
describe <- function(m, x) {
  w <- weights(m,type='prior')
  response <- getME(m,'y')
  list(nobs=nobs(m), model_frame_rows=nrow(model.frame(m)),
    positive_prior_weight_rows=sum(w>0), zero_prior_weight_rows=sum(w==0),
    prior_weight_sum=sum(w), finite_internal_responses=all(is.finite(response)),
    zero_time_conditional_loglik_sum=sum(dbinom(response[x$tottime==0]*w[x$tottime==0],
      size=w[x$tottime==0],prob=fitted(m)[x$tottime==0],log=TRUE)),
    zero_time_prior_weights=unname(w[x$tottime==0]),
    zero_time_internal_responses=unname(response[x$tottime==0]),
    offset=if(is.null(model.offset(model.frame(m)))) NULL else
      unname(model.offset(model.frame(m))),
    fixed_effects=as.list(fixef(m)), logLik=as.numeric(logLik(m)),
    singular=isSingular(m), convergence=m@optinfo$conv,
    conditional_fitted=unname(fitted(m)),
    fixed_only_fitted=unname(predict(m,re.form=NA,type='response')))
}
pair <- function(x, endpoint, optimizer=NULL) {
  full <- fit(x,endpoint,FALSE,optimizer)
  null <- fit(x,endpoint,TRUE,optimizer)
  stat <- 2*(as.numeric(logLik(full))-as.numeric(logLik(null)))
  df <- attr(logLik(full),'df')-attr(logLik(null),'df')
  list(full=full,null=null,comparison=list(chisq=stat,df=df,p=pchisq(stat,df,lower.tail=FALSE)))
}
models <- list(); private <- list(); sensitivity <- list()
attempt <- function(expr) tryCatch(expr,error=function(e) list(error=conditionMessage(e)))
for(endpoint in c('exploration','expectation')) {
  cat('baseline',endpoint,'\n')
  b <- pair(d,endpoint)
  cat('optimizer bobyqa',endpoint,'\n')
  alt <- attempt(pair(d,endpoint,'bobyqa'))
  pos <- d[d$tottime>0,,drop=FALSE]
  cat('positive-time only',endpoint,'\n')
  z <- attempt(pair(pos,endpoint))
  private[[endpoint]] <- list(full=describe(b$full,d),null=describe(b$null,d),
    positive_time=if(!is.null(z$error)) z else list(full=describe(z$full,pos),null=describe(z$null,pos)),
    optimizer=if(!is.null(alt$error)) alt else list(full=describe(alt$full,d),null=describe(alt$null,d)))
  summarize <- function(m) {
    y <- describe(m,d)
    y[c('nobs','model_frame_rows','positive_prior_weight_rows','zero_prior_weight_rows',
      'prior_weight_sum','finite_internal_responses','zero_time_conditional_loglik_sum',
      'fixed_effects','logLik','singular','convergence')]
  }
  models[[endpoint]] <- list(full=summarize(b$full),null=summarize(b$null),
    comparison=b$comparison,
    optimizer_comparison=if(!is.null(alt$error)) alt else alt$comparison,
    optimizer_max_fitted_difference=if(is.null(alt$error)) max(abs(fitted(b$full)-fitted(alt$full))) else NULL,
    positive_time_comparison=if(!is.null(z$error)) z else z$comparison,
    zero_time_removal_logLik_delta=if(is.null(z$error)) c(full=as.numeric(logLik(z$full)-logLik(b$full)),
      null=as.numeric(logLik(z$null)-logLik(b$null))) else NULL,
    zero_time_removal_max_positive_fitted_delta=if(is.null(z$error)) max(abs(fitted(z$full)-fitted(b$full)[d$tottime>0])) else NULL)
  for(unit in c('individual','playbackID')) {
    for(id in sort(unique(as.character(d[[unit]])))) {
      cat('omit',endpoint,unit,id,'\n')
      x <- droplevels(d[as.character(d[[unit]])!=id,,drop=FALSE])
      r <- tryCatch({
        q <- pair(x,endpoint)
        list(comparison=q$comparison,n_rows=nrow(x),
          full_singular=isSingular(q$full),null_singular=isSingular(q$null),
          full_convergence=q$full@optinfo$conv,null_convergence=q$null@optinfo$conv)
      },error=function(e) list(error=conditionMessage(e)))
      sensitivity[[paste(endpoint,unit,id,sep=':')]] <- r
    }
  }
}
aggregate_sensitivity <- list()
for(endpoint in c('exploration','expectation')) for(unit in c('individual','playbackID')) {
  s <- sensitivity[startsWith(names(sensitivity),paste(endpoint,unit,sep=':'))]
  good <- Filter(function(x) is.null(x$error),s)
  aggregate_sensitivity[[paste(endpoint,unit,sep=':')]] <- list(attempted=length(s),
    completed=length(good), errors=length(s)-length(good),
    chisq_range=range(vapply(good,function(x)x$comparison$chisq,numeric(1))),
    p_range=range(vapply(good,function(x)x$comparison$p,numeric(1))),
    full_singular_count=sum(vapply(good,function(x)x$full_singular,logical(1))),
    null_singular_count=sum(vapply(good,function(x)x$null_singular,logical(1))),
    convergence_message_count=sum(vapply(good,function(x)
      length(x$full_convergence$lme4$messages)>0 || length(x$null_convergence$lme4$messages)>0,logical(1))))
}
write_json(list(models=private,sensitivity=sensitivity),file.path(out,'private-models.json'),
  pretty=TRUE,auto_unbox=TRUE,digits=17,null='null')
writeLines(capture.output(sessionInfo()),file.path(out,'session.txt'))
write_json(list(status='SOURCE_SOFTWARE_REPRODUCTION_WITH_EXPLORATORY_SENSITIVITY',
  R=R.version.string,lme4=as.character(packageVersion('lme4')),
  Matrix=as.character(packageVersion('Matrix')),rows=nrow(d),subject_session_units=57,
  subjects=10,sessions=12,zero_time_rows=sum(d$tottime==0),positive_time_rows=sum(d$tottime>0),
  shared_columns_equal=shared,derived_fields_verified=c('nolooktime=tottime-looktime',
    'logtottime=log1p(tottime)','explore=peer OR probe'),
  models=models,sensitivity=aggregate_sensitivity,warnings=as.list(table(warnings)),
  historical_R_3_4_3_lme4_1_1_15='NOT_AVAILABLE_NOT_TESTED',
  limits=paste0('Frozen source formulas; default optimizer versus bobyqa is optimizer sensitivity, ',
    'not software-version equivalence. Zero-time removal changes exploration opportunity estimand. ',
    'No causal caller-training identification, call-order test, independent replication or scientific admission.')),
  file.path(out,'aggregate.json'),pretty=TRUE,auto_unbox=TRUE,digits=17,null='null')
