Pure functional programming lends itself well to [property-based testing](https://hypothesis.works/articles/what-is-property-based-testing/). In Python, property based testing is most often done using the [hypothesis](https://hypothesis.readthedocs.io/en/latest/) library. 

To make it easy to test code that uses `pfun`, a number of useful hypothesis test strategies are made available if hypothesis is installed. To use the version of hypothesis that `pfun` is tested against, you can install it using `pip install pfun[test]`.
