#!/usr/bin/env hy
; -*- mode: hy -*-
; Date: 30.06.2019 [dd.mm.yyyy]
; Author: Jørgen Bele Reinfjell
; Description: 
;   Utility to extract grades from 
;   fsweb writen in hy 


(import requests
        [bs4 [BeautifulSoup]]
        [json [dumps :as dump-json]])

(setv base-url "https://fsweb.no/studentweb/"
      results-endpoint "resultater.jsf"
      default-cookie "JSESSIONID=\"XXXXXXXXXXXX\"")

                                ; TODO: cleanup
(defn do-request [endpoint &optional [cookie default-cookie]]
  (setv headers {"Cookie" cookie})
  (setv url (+ base-url endpoint))
  (setv resp (.get requests url :headers headers))
  (if (. resp ok)
      (return (. resp text))))

(defmacro find-class-as [obj class as block]
  `(as-> (.find ~obj "td" :class_ ~class) ~as ~block))

(defmacro unless-empty-last [var block &optional condition]
  (if (none? condition)
      `(unless (empty? ~var) (last ~block))
      `(unless (or ~condition (empty? ~var)) (last ~block))))


(defn tr-to-dict [tr]
  "Extracts data from a results table row"
  (setv course (-> (.find tr "td" :class_ "col2Emne")
                   (.find "div" :class_ "column-info")))
  {
   "semester"      (find-class-as tr "col1Semester" sem
                                  (unless-empty-last sem (. sem stripped-strings)))

   "course_name"   (unless-empty-last course (. course stripped-strings))

   "course_code"   (unless-empty-last course (butlast (. course stripped-strings)))

   "grading"       (find-class-as tr "col3Vurdering" grading
                                  (unless-empty-last grading (. grading stripped-strings)))

   "result_date"   (find-class-as tr "col4Resultatdato" resdate
                                  (unless-empty-last resdate
                                                     (. resdate stripped-strings) (none? resdate)))

   "candidate_num" (find-class-as tr "col5Kandnr" candnum
                                  (unless-empty-last candnum (. candnum stripped-strings)))

   "result" (find-class-as tr "col6Resultat" result
                           (unless-empty-last result
                                              (. result stripped-strings) (none? result)))

   "points" (find-class-as tr "col7Studiepoeng" studpoint
                           (unless-empty-last studpoint
                                              (. studpoint stripped-strings) (none? studpoint)))
   })

(defn get-results [&optional [cookie default-cookie]]
  (setv html (do-request results-endpoint))
  ;(print html)
                                ; parse the html using bs4
  (setv soup (BeautifulSoup html :features "lxml"))
  (setv table (.find soup "table" :id "resultatlisteForm:HeleResultater:resultaterPanel"))
  (setv trs (+ (.find-all table "tr" :class_ "none") (.find-all table "tr" :class_ "resultatTop")))
  (return (list (map tr-to-dict (filter None trs)))))

(defn remove-null-fields [d]
  (setv out {})
  (for [[k v] (.items d)]
    (unless (none? v)
      (assoc out k v)))
  out)

(defn lton [letter-grade]
  (setv mapping {"A" 5 "B" 4 "C" 3 "D" 2 "E" 1 "F" 0 "Bestått" None "Ikke møtt" None})
  (return (get mapping letter-grade)))

(defn extract-grade-and-points [entry pred]
  [(lton (get entry "result")) (as-> (get entry "points") points
                                     (unless
                                       (or (not (pred entry)) (none? points))
                                       (float (.replace points "," "."))))])

(defn calc-avg-grade [&optional pred]
  "Calculate the average grade from entries where (pred entry) is true"
  (if (none? pred) ; no predicate was specified so create one which always returns true
      (setv pred (constantly True)))
  (setv tuples (list (filter (fn [tuple] 
                               (every? (fn [t] (not (none? t))) tuple))
                             (map (fn [arg] (extract-grade-and-points arg pred))
                                  (get-results)))))
  (print tuples)
  (round (/ (sum (map (fn [e] (* (first e) (second e))) tuples))
            (sum (map second tuples))) 1))

(defmain [&rest args]
  (global default-cookie)
  (setv default-cookie f"JSESSIONID=\"{(first (drop 1 args))}\"")
  (print default-cookie)

  (as-> (first (drop 2 args)) arg
        (cond
          [(= arg "--avg")
           (as-> (calc-avg-grade ;(fn [entry] (= "2019 VÅR" (get entry "semester"))))
                                ) avg
                 (print f"Total Average: {avg}"))]

          [(= arg "--dump-json") (print (dump-json (list (map remove-null-fields (get-results)))))])))
