# ARS derived algorithm diagnostic. Never an exact source-code execution.
# Original source is read unmodified from its private, hash-verified archive.
args <- commandArgs(trailingOnly=TRUE)
stopifnot(length(args)==2L)
root <- normalizePath(args[1]); out <- args[2]
stopifnot(!file.exists(out), dir.exists(dirname(out)))
stopifnot(digest::digest(file=file.path(root,'sources/xdata.txt'),algo='sha256')=='84ad7b48bb41cf55b4f92c5a2fcf57780ad5590b0b4d941684f3a843b1abd6a4',
 digest::digest(file=file.path(root,'sources/03_weighted_mca_permutation_test.R'),algo='sha256')=='1deb8993ed29df05704a871c150b09c0f938737f189a68fe1a02d87594d53ae4')
stopifnot(dir.create(out,mode='0700'))
out <- normalizePath(out)
.libPaths(c(file.path(root,'rlib'),.libPaths()))
library(FactoMineR); library(jsonlite)
stopifnot(R.version.string == 'R version 4.6.1 (2026-06-24)',
          as.character(packageVersion('FactoMineR')) == '2.18')
source_text <- readLines(file.path(root,'sources/03_weighted_mca_permutation_test.R'))
run_cached <- function(B) {
 set.seed(123)
 e <- new.env(parent=globalenv()); cache <- NULL; active <- NULL; fixed <- NULL; draws <- NULL
 e$MCA <- function(X, quali.sup, quanti.sup, row.w, ncp) {
  a <- X[, -c(quali.sup,quanti.sup),drop=FALSE]
  if (is.null(cache)) {
   rng_before <- .Random.seed
   cache <<- FactoMineR::MCA(X,quali.sup=quali.sup,quanti.sup=quanti.sup,
                          row.w=row.w,ncp=ncp,graph=FALSE)
   rng_after <- .Random.seed
   # Infer and validate the headless irlba normal-draw count against the exact
   # complete RNG state. Never assume that skipping numerical work skips RNG.
   for (n in 1:3000) {
    assign('.Random.seed',rng_before,envir=globalenv()); rnorm(n)
    if (identical(.Random.seed,rng_after)) { draws <<- n; break }
   }
   stopifnot(!is.null(draws))
   assign('.Random.seed',rng_after,envir=globalenv())
   active <<- a; fixed <<- row.w
  } else {
   stopifnot(identical(a,active), identical(row.w,fixed), ncp==5,
             identical(quali.sup,1:4), identical(quanti.sup,c(5,6)))
   rnorm(draws)
  }
  # Audited graphics-only RNG consumption in this pinned runtime.
  sample.int(.Machine$integer.max,1L)
  cache
 }
 code <- source_text
 stopifnot(sum(code=='nperm <- 100')==1)
 code[code=='nperm <- 100'] <- paste('nperm <-',B)
 eval(parse(text=code),envir=e)
 list(R_obs=e$R_obs,R_perm=e$R_perm,pval=e$pval,random_seed=.Random.seed,headless_normal_draws=draws)
}
setwd(file.path(root,'sources'))
baseline <- readRDS(file.path(root,'original-100-managed/source-results.rds'))
small <- run_cached(100)
stopifnot(max(abs(small$R_perm-baseline$R_perm))<1e-10,
          abs(small$R_obs-baseline$R_obs)<1e-10,
          identical(small$random_seed,baseline$random_seed))
large <- run_cached(10000)
prefix <- readRDS(file.path(root,'derivative-10000-guarded-20261020T211358Z/permutation-checkpoint.rds'))
stopifnot(length(prefix$R_perm)==prefix$completed_permutations,
          prefix$completed_permutations>5000,
          identical(head(large$R_perm,length(prefix$R_perm))>=large$R_obs,prefix$R_perm>=prefix$R_obs),
          max(abs(head(large$R_perm,length(prefix$R_perm))-prefix$R_perm))<1e-10)
p <- large$pval; B <- length(large$R_perm)
receipt <- list(classification='DERIVED_CACHED_GEOMETRY_ALGORITHM_DIAGNOSTIC_NOT_EXACT_SOURCE_REPLAY',
 R=R.version.string,FactoMineR=as.character(packageVersion('FactoMineR')),
 nperm=B,observed_R=large$R_obs,pvalue=p,exceedances=sum(large$R_perm>=large$R_obs),headless_normal_draws=large$headless_normal_draws,
 monte_carlo_se=sqrt(p*(1-p)/B),
 reference_pvalue=0.2597,exact_published_result_reproduced=FALSE,
 baseline_100_max_abs_error=max(abs(small$R_perm-baseline$R_perm)),
 baseline_100_final_rng_identical=identical(small$random_seed,baseline$random_seed),
 interrupted_prefix_permutations=length(prefix$R_perm),
 interrupted_prefix_max_abs_error=max(abs(head(large$R_perm,length(prefix$R_perm))-prefix$R_perm)),
 limits='MCA active geometry reused only after active inputs/weights/arguments equality checks; supplementary projections are not regenerated. Equivalent statistic checked against B100 and interrupted source prefix at absolute statistic tolerance 1e-10, with identical prefix exceedance classifications. Not full-source B10000, author result, null validity, biological evidence, semantic inference, or admission. Original run remains interrupted.')
write_json(receipt,file.path(out,'cached-geometry-receipt.json'),pretty=TRUE,auto_unbox=TRUE,digits=17)
saveRDS(large,file.path(out,'cached-geometry-results.rds'))
cat(toJSON(receipt,auto_unbox=TRUE,digits=17),'\n')
